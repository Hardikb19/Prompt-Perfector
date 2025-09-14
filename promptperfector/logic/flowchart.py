import uuid
import json

class Node:
    def __init__(self, text, node_id=None, connectsTo=None, connectsFrom=None, subject=None):
        self.id = node_id or str(uuid.uuid4())
        self.text = text
        self.subject = subject  # New field for node subject/title
        self.connectsTo = connectsTo or []
        self.connectsFrom = connectsFrom or []

    def to_dict(self):
        return {
            'id': self.id,
            'subject': self.subject if self.subject is not None else '',
            'text': self.text,
            'connectsTo': self.connectsTo if self.connectsTo else None,
            'connectsFrom': self.connectsFrom if self.connectsFrom else None
        }

class FlowchartModel:
    def __init__(self, nodes=None):
        self.nodes = nodes or []

    @classmethod
    def from_json(cls, json_data):
        data = json_data if isinstance(json_data, dict) else json.loads(json_data)
        nodes = [Node(
            n['text'],
            node_id=n['id'],
            connectsTo=n.get('connectsTo') or [],
            connectsFrom=n.get('connectsFrom') or [],
            subject=n.get('subject') if 'subject' in n else None
        ) for n in data.get('nodes', [])]
        return cls(nodes)

    def add_node(self, text, subject=None):
        node = Node(text, subject=subject)
        self.nodes.append(node)
        return node

    def to_json(self):
        return {'nodes': [n.to_dict() for n in self.nodes]}
