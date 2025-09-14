from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsTextItem, QGraphicsRectItem, QGraphicsItem, QGraphicsLineItem, QMenu, QInputDialog, QGraphicsEllipseItem, QDialog, QFormLayout, QLineEdit, QDialogButtonBox
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QMouseEvent, QPainter, QAction, QPolygonF
from PySide6.QtCore import Qt, QPointF, QRectF
from promptperfector.logic.logger import log_debug, log_info, log_error

# Custom line with arrowhead for connectors
class ArrowLineItem(QGraphicsLineItem):
    def __init__(self, x1, y1, x2, y2, *args, **kwargs):
        super().__init__(x1, y1, x2, y2, *args, **kwargs)
        self.setZValue(-1)
        self.arrow_size = 16
    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        line = self.line()
        if line.length() == 0:
            return
        # Draw multiple arrowheads along the line
        arrow_count = max(1, int(line.length() // 60))  # At least 1, more if long
        for i in range(arrow_count):
            t = (i + 1) / (arrow_count + 1)
            p = QPointF(
                line.x1() + (line.x2() - line.x1()) * t,
                line.y1() + (line.y2() - line.y1()) * t
            )
            angle = line.angle()
            # Arrow points
            arrow_p1 = p + QPointF(-self.arrow_size * 0.5, self.arrow_size * 0.5)
            arrow_p2 = p + QPointF(-self.arrow_size * 0.5, -self.arrow_size * 0.5)
            def rotate_point(pt, center, angle_deg):
                from math import radians, cos, sin
                angle_rad = radians(angle_deg)
                dx = pt.x() - center.x()
                dy = pt.y() - center.y()
                x_new = dx * cos(angle_rad) - dy * sin(angle_rad)
                y_new = dx * sin(angle_rad) + dy * cos(angle_rad)
                return QPointF(center.x() + x_new, center.y() + y_new)
            arrow_p1 = rotate_point(arrow_p1, p, -angle)
            arrow_p2 = rotate_point(arrow_p2, p, -angle)
            arrow_head = QPolygonF([p, arrow_p1, arrow_p2])
            painter.setBrush(QBrush(Qt.black))
            painter.drawPolygon(arrow_head)


class FlowchartNode(QGraphicsRectItem):
    def update_text_item(self):
        log_debug(f'Showing subject/text in node update_text_item ${self.node_id}, ${self.subject}, ${self.text}')
        display = self.subject.strip() if len(self.subject.strip()) > 0 else self.text
        log_debug(f'Computed display text: "{display}"')
        self.text_item.setPlainText(display)
        log_debug(f'Set text item plain text to: "{self.text_item.toPlainText()}"')
        self.update_text_box_size()

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text
        self.update_text_item()
        if self.canvas_ref and hasattr(self.canvas_ref, 'on_update') and text.strip():
            log_info(f"Node text updated: id={self.node_id}, new_text='{text}'")
            self.canvas_ref.on_update()

    def get_subject(self):
        return self.subject

    def set_subject(self, subject):
        self.subject = subject
        self.update_text_item()
        if self.canvas_ref and hasattr(self.canvas_ref, 'on_update'):
            log_info(f"Node subject updated: id={self.node_id}, new_subject='{subject}'")
            self.canvas_ref.on_update()

    def edit_subject_and_text(self):
        dialog = QDialog()
        dialog.setWindowTitle("Edit Node")
        layout = QFormLayout(dialog)
        subject_edit = QLineEdit(dialog)
        subject_edit.setText(self.get_subject())
        text_edit = QLineEdit(dialog)
        text_edit.setText(self.get_text())
        layout.addRow("Subject (title):", subject_edit)
        layout.addRow("Text (content):", text_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() == QDialog.Accepted:
            self.set_subject(subject_edit.text())
            self.set_text(text_edit.text())
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            # Update all connectors attached to this node
            if self.canvas_ref:
                for from_id, to_id, connector in getattr(self.canvas_ref, "connectors", []):
                    if from_id == self.node_id or to_id == self.node_id:
                        start_node = self.canvas_ref.nodes.get(from_id)
                        end_node = self.canvas_ref.nodes.get(to_id)
                        if start_node and end_node:
                            connector.setLine(
                                start_node.scenePos().x(), start_node.scenePos().y(),
                                end_node.scenePos().x(), end_node.scenePos().y()
                            )
        return super().itemChange(change, value)
    def mousePressEvent(self, event):
        log_debug(f"[Node {getattr(self, 'node_id', None)}] mousePressEvent: button={event.button()}, modifiers={event.modifiers()}, pos={event.pos()}")
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        log_debug(f"[Node {getattr(self, 'node_id', None)}] contextMenuEvent at {event.pos()} (scene: {event.scenePos()})")
        menu = QMenu()
        edit_both_action = QAction("Edit Node (Subject/Text)", menu)
        delete_action = QAction("Delete", menu)
        menu.addAction(edit_both_action)
        menu.addAction(delete_action)
        action = menu.exec(event.screenPos())
        if action == edit_both_action:
            self.edit_subject_and_text()
        elif action == delete_action:
            scene = self.scene()
            to_remove = []
            for item in list(scene.items()):
                if isinstance(item, QGraphicsLineItem):
                    log_info(f"Checking item in scene for deletion: {type(item).__name__} and  if it has a from_id or to_id. From_id={getattr(item, 'from_id', None)}, to_id={getattr(item, 'to_id', None)}")
                    if hasattr(item, 'from_id') and (item.from_id == self.node_id or item.to_id == self.node_id):
                        log_info(f"Deleting connector attached to node: node_id={self.node_id}, connector=({getattr(item, 'from_id', None)}->{getattr(item, 'to_id', None)})")
                        to_remove.append(item)
            for item in to_remove:
                scene.removeItem(item)
            if self.canvas_ref:
                self.canvas_ref.connectors = [c for c in self.canvas_ref.connectors if c[0] != self.node_id and c[1] != self.node_id]
            log_info(f"Deleting node: id={self.node_id}")
            scene.removeItem(self)
        if self.canvas_ref and hasattr(self.canvas_ref, 'on_update'):
            self.canvas_ref.on_update()
        return

    def hoverEnterEvent(self, event):
        log_debug(f"[Node {getattr(self, 'node_id', None)}] hoverEnterEvent")
        self.show_connector_buttons(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        log_debug(f"[Node {getattr(self, 'node_id', None)}] hoverLeaveEvent")
        if not getattr(self.scene(), '_show_all_connectors', False):
            self.show_connector_buttons(False)
        super().hoverLeaveEvent(event)
    # Reference to parent canvas for autosave
    canvas_ref = None
    def __init__(self, text, node_id, pos=QPointF(0,0), color=QColor("#ffc0cb"), subject=None):
        self.node_id = node_id
        log_debug(f"Creating node: id={node_id}, text='{text}', pos=({pos.x()}, {pos.y()})")
        # Dynamic sizing: initial size
        self.default_width = 120
        self.max_width = 240
        self.margin = 10
        super().__init__(-self.default_width//2, -30, self.default_width, 60)
        self.setBrush(QBrush(color))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.AllButtons)
        log_debug(f"FlowchartNode created: id={node_id}, focusable={self.flags() & QGraphicsItem.ItemIsFocusable != 0}")
        self.text_item = QGraphicsTextItem(self)
        self.text_item.setTextInteractionFlags(Qt.NoTextInteraction)
        self.text_item.setDefaultTextColor(Qt.black)
        self.text_item.setFont(QFont("Arial", 12))

        # log_debug for subject/text/pos already above
        self.text = text
        self.subject = subject if subject is not None else ''
        self.setPos(pos)

        # Connector buttons (hidden by default)
        self.connector_buttons = {}
        for name, (dx, dy) in {
            'top': (0, -30),
            'bottom': (0, 30),
            'left': (-self.default_width//2, 0),
            'right': (self.default_width//2, 0)
        }.items():
            btn = QGraphicsEllipseItem(-8, -8, 16, 16, self)
            btn.setPos(dx, dy)
            btn.setBrush(QBrush(QColor("#00ccff")))
            btn.setPen(QPen(Qt.black, 1))
            btn.setZValue(2)
            btn.setVisible(False)
            btn.setData(0, name)
            btn.setAcceptedMouseButtons(Qt.LeftButton)
            btn.setFlag(QGraphicsItem.ItemIsSelectable, True)
            btn.setFlag(QGraphicsItem.ItemIsFocusable, True)
            # installSceneEventFilter will be called after node is added to scene
            log_debug(f"Connector button '{name}' for node {node_id} set to accept left button only and selectable/focusable.")
            self.connector_buttons[name] = btn
        self.set_text(text)
        self.subject = subject if subject is not None else ''

    def update_text_box_size(self):
        # Calculate required width/height for text
        doc = self.text_item.document()
        doc.setDefaultFont(self.text_item.font())
        # Try to fit in default width, then max width
        doc.setTextWidth(self.default_width - 2*self.margin)
        if doc.idealWidth() < self.max_width - 2*self.margin:
            width = max(self.default_width, int(doc.idealWidth()) + 2*self.margin)
            text_width = width - 2*self.margin
        else:
            width = self.max_width
            text_width = width - 2*self.margin
        self.text_item.setTextWidth(text_width)
        height = int(doc.size().height()) + 2*self.margin
        # Update rect
        self.setRect(-width//2, -height//2, width, height)
        # Center text
        self.text_item.setPos(-text_width//2, -doc.size().height()/2)
        # Move connector buttons
        self.connector_buttons['left'].setPos(-width//2, 0)
        self.connector_buttons['right'].setPos(width//2, 0)
        self.connector_buttons['top'].setPos(0, -height//2)
        self.connector_buttons['bottom'].setPos(0, height//2)


    def install_connector_event_filters(self):
        for btn in self.connector_buttons.values():
            btn.installSceneEventFilter(self)

    # --- Connector button event filter ---
    def sceneEventFilter(self, watched, event):
        from PySide6.QtCore import QEvent
        from promptperfector.logic.logger import log_debug
        if isinstance(watched, QGraphicsEllipseItem):
            log_debug(f"[ConnectorButton] sceneEventFilter: event={event.type()}, button={getattr(event, 'button', lambda: None)() if hasattr(event, 'button') else None}, node_id={self.node_id}, btn={watched.data(0)}")
            if event.type() == QEvent.GraphicsSceneMousePress and event.button() == Qt.LeftButton:
                log_debug(f"[ConnectorButton] MousePress detected on node {self.node_id} btn {watched.data(0)}")
                if self.canvas_ref:
                    return self.canvas_ref.handle_connector_button_click(self, watched)
        return False

    def hoverEnterEvent(self, event):
        self.show_connector_buttons(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        # Only hide if not in global drag mode
        if not getattr(self.scene(), '_show_all_connectors', False):
            self.show_connector_buttons(False)
        super().hoverLeaveEvent(event)

    def show_connector_buttons(self, show):
        for btn in self.connector_buttons.values():
            btn.setVisible(show)

    def mousePressEvent(self, event):
        # Only handle selection/movement, not editing
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.edit_subject_and_text()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def get_text(self):
        return self.text_item.toPlainText()

    def set_text(self, text):
        self.update_text_item()
        self.update_text_box_size()
        # Only autosave if this is a text modification (not node creation)
        if self.canvas_ref and hasattr(self.canvas_ref, 'on_update') and text.strip():
            log_info(f"Node text updated: id={self.node_id}, new_text='{text}'")
            self.canvas_ref.on_update()

    def boundingRect(self):
        return self.rect()

    def get_position(self):
        return self.scenePos()

    def set_position(self, pos):
        self.setPos(pos)

    def clip_text(self, text):
        # Clip text to fit in box, add ellipsis if too long
        max_chars = 30
        return text if len(text) <= max_chars else text[:max_chars-3] + '...'

    # contextMenuEvent is defined later in the file; remove this duplicate.


class FlowchartCanvas(QGraphicsView):
    # --- Connector creation logic ---
    def handle_connector_button_click(self, node, btn):
        # If not currently dragging, start a new connector
        if not hasattr(self, '_pending_connector') or self._pending_connector is None:
            self._pending_connector = (node, btn)
            btn.setBrush(QBrush(QColor("#ffcc00")))  # Highlight active
            log_debug(f"[Canvas] Started connector from node {node.node_id} side {btn.data(0)}")
            return True
        # If already dragging, finish connector if valid
        start_node, start_btn = self._pending_connector
        if node is not start_node:
            # Draw connector
            start_pos = start_node.scenePos()
            end_pos = node.scenePos()
            connector = ArrowLineItem(start_pos.x(), start_pos.y(), end_pos.x(), end_pos.y())
            connector.setPen(QPen(Qt.black, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            connector.from_id = start_node.node_id
            connector.to_id = node.node_id
            self.scene().addItem(connector)
            self.connectors.append((start_node.node_id, node.node_id, connector))
            log_info(f"Created connector: {start_node.node_id} -> {node.node_id}")
            if hasattr(self, 'on_update'):
                self.on_update()
        # Reset highlight
        start_btn.setBrush(QBrush(QColor("#00ccff")))
        self._pending_connector = None
        return True
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setSceneRect(-2000, -2000, 4000, 4000)
        self.nodes = {}
        self.connectors = []
        self._dragging_connector = None
        self._drag_start_node = None
        self._drag_start_btn = None
        self._node_colors = [QColor("#ffc0cb"), QColor("#ff6666"), QColor("#ffff66")]
        self._color_idx = 0
        self.setMouseTracking(True)
        self.on_update = lambda: None
    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        log_debug(f"[Canvas] contextMenuEvent at {event.pos()} on {type(item).__name__ if item else 'None'}")
        if isinstance(item, QGraphicsLineItem):
            menu = QMenu()
            delete_action = QAction("Delete Connector", menu)
            menu.addAction(delete_action)
            action = menu.exec(event.globalPos())
            if action == delete_action:
                log_info(f"Deleted connector via context menu: {getattr(item, 'from_id', None)} -> {getattr(item, 'to_id', None)}")
                self.scene().removeItem(item)
                # Remove from connectors list
                self.connectors = [c for c in self.connectors if c[2] is not item]
            return
        if isinstance(item, FlowchartNode):
            log_debug(f"[Canvas] contextMenuEvent: node under mouse (id={getattr(item, 'node_id', None)}), but event not routed to node. Node flags: {item.flags()}")
            return
        log_debug("[Canvas] contextMenuEvent: calling super() for empty space or unknown item.")
        super().contextMenuEvent(event)
    # --- Model/DB sync ---
    def export_to_model(self):
        # Export nodes and connectors to FlowchartModel JSON
        log_debug(f"Exporting model: {len(self.connectors)} connectors present.")
        for idx, (from_id, to_id, _) in enumerate(self.connectors):
            log_debug(f"Connector {idx}: {from_id} -> {to_id}")
        nodes = []
        for node_id, node in self.nodes.items():
            connectsTo = [to_id for from_id, to_id, _ in self.connectors if from_id == node_id]
            connectsFrom = [from_id for from_id, to_id, _ in self.connectors if to_id == node_id]
            pos = node.get_position()
            nodes.append({
                'id': node_id,
                'subject': node.get_subject() if hasattr(node, 'get_subject') else '',
                'text': node.get_text(),
                'connectsTo': connectsTo if connectsTo else None,
                'connectsFrom': connectsFrom if connectsFrom else None,
                'pos': [pos.x(), pos.y()]
            })
        return {'nodes': nodes}

    def import_from_model(self, model_json):
        # Clear scene
        self.scene().clear()
        self.nodes = {}
        self.connectors = []
        nodes = model_json.get('nodes', [])
        log_debug(f"Importing model: {len(nodes)} nodes")
        # Add nodes
        for n in nodes:
            pos = QPointF(*(n.get('pos', [0, 0])))
            subject = n.get('subject', '')
            text = n.get('text', '')
            # Backward compatibility: if subject is missing or empty, use text as subject for display
            color = QColor("#ffc0cb")
            node = FlowchartNode(text, n['id'], pos, color, subject=subject)
            node.setAcceptHoverEvents(True)
            node.canvas_ref = self
            self.scene().addItem(node)
            node.install_connector_event_filters()
            self.nodes[n['id']] = node
        # Add connectors
        for n in nodes:
            from_node = self.nodes[n['id']]
            for to_id in n.get('connectsTo') or []:
                if to_id in self.nodes:
                    to_node = self.nodes[to_id]
                    start = from_node.scenePos()
                    end = to_node.scenePos()
                    connector = ArrowLineItem(start.x(), start.y(), end.x(), end.y())
                    connector.setPen(QPen(Qt.black, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    connector.from_id = from_node.node_id
                    connector.to_id = to_node.node_id
                    self.scene().addItem(connector)
                    self.connectors.append((from_node.node_id, to_node.node_id, connector))
                    log_info(f"Imported connector: {from_node.node_id} -> {to_node.node_id}")
        # Fit view to all items if any exist
        items_rect = self.scene().itemsBoundingRect()
        if not items_rect.isNull():
            self.fitInView(items_rect, Qt.KeepAspectRatio)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setSceneRect(-2000, -2000, 4000, 4000)
        self.nodes = {}
        self.connectors = []
        self._dragging_connector = None
        self._drag_start_node = None
        self._node_colors = [QColor("#ffc0cb"), QColor("#ff6666"), QColor("#ffff66")]
        self._color_idx = 0

    def mouseDoubleClickEvent(self, event):
        # Only create node if double-clicked on empty canvas
        item = self.itemAt(event.pos())
        if item is None:
            pos = self.mapToScene(event.pos())
            node_id = f"node_{len(self.nodes)+1}"
            color = self._node_colors[self._color_idx % len(self._node_colors)]
            self._color_idx += 1
            node = FlowchartNode("Editable text box", node_id, pos, color)
            node.setAcceptHoverEvents(True)
            node.canvas_ref = self
            self.scene().addItem(node)
            node.install_connector_event_filters()
            self.nodes[node_id] = node
            log_info(f"User double-clicked to create node: id={node_id}, pos=({pos.x()}, {pos.y()})")
        super().mouseDoubleClickEvent(event)

    def mouseDoubleClickEventFake(self, text):
        # Add a node with custom text (for LLM simulation)
        pos = QPointF(0, 0)
        node_id = f"node_{len(self.nodes)+1}"
        color = self._node_colors[self._color_idx % len(self._node_colors)]
        self._color_idx += 1
        node = FlowchartNode(text, node_id, pos, color)
        self.scene().addItem(node)
        node.install_connector_event_filters()
        self.nodes[node_id] = node

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        log_debug(f"[Canvas] contextMenuEvent at {event.pos()} on {type(item).__name__ if item else 'None'}")
        # Handle connector context menu
        if isinstance(item, QGraphicsLineItem):
            menu = QMenu()
            delete_action = QAction("Delete Connector", menu)
            menu.addAction(delete_action)
            action = menu.exec(event.globalPos())
            if action == delete_action:
                log_info(f"Deleted connector via context menu: {getattr(item, 'from_id', None)} -> {getattr(item, 'to_id', None)}")
                self.scene().removeItem(item)
                self.connectors = [c for c in self.connectors if c[2] is not item]
                log_debug(f"After deletion, {len(self.connectors)} connectors remain.")
                log_debug(f"calling debug on self: {self}")
                if hasattr(self, 'on_update'):
                    log_debug("Calling on_update after connector deletion.")
                    self.on_update()
            return
        # If right-clicked on a node, let the node handle its own context menu event
        if isinstance(item, FlowchartNode):
            log_debug(f"[Canvas] contextMenuEvent: node under mouse (id={getattr(item, 'node_id', None)}), event not handled by canvas.")
            return
        # If right-clicked on a connector button, let the parent node handle it
        if isinstance(item, QGraphicsEllipseItem) and item.parentItem() and isinstance(item.parentItem(), FlowchartNode):
            log_debug(f"[Canvas] contextMenuEvent: connector button under mouse for node id={getattr(item.parentItem(), 'node_id', None)}, event not handled by canvas.")
            return
        # Otherwise, propagate to default (empty space)
        log_debug("[Canvas] contextMenuEvent: calling super() for empty space or unknown item.")
        super().contextMenuEvent(event)

    # mouseMoveEvent and mouseReleaseEvent are no longer needed for connector creation
    
    def mouseDoubleClickEventFake(self, text):
        # Add a node with custom text (for LLM simulation)
        pos = QPointF(0, 0)
        node_id = f"node_{len(self.nodes)+1}"
        color = self._node_colors[self._color_idx % len(self._node_colors)]
        self._color_idx += 1
        node = FlowchartNode(text, node_id, pos, color)
        self.scene().addItem(node)
        self.nodes[node_id] = node