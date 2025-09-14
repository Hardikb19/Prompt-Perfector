from llama_cpp import Llama

class LlamaCppRunner:
    """
    Manages a llama-cpp-python Llama instance for a given model. In-process, cross-platform.
    """
    def __init__(self, model_path, n_threads=8, n_ctx=4096):
        self.model_path = model_path
        self.n_threads = n_threads
        self.n_ctx = n_ctx
        self.llm = None

    def start(self):
        from promptperfector.logic.logger import log_debug
        import time
        log_debug(f"LlamaCppRunner.start() called for model: {self.model_path}, n_ctx={self.n_ctx}, n_threads={self.n_threads}")
        if self.llm:
            log_debug("LlamaCppRunner: Existing model found, stopping before reload.")
            self.stop()
        try:
            t0 = time.perf_counter()
            self.llm = Llama(model_path=self.model_path, n_ctx=self.n_ctx, n_threads=self.n_threads, verbose=False)
            t1 = time.perf_counter()
            log_debug(f"LlamaCppRunner: Model loaded successfully in {t1-t0:.2f} seconds.")
        except Exception as e:
            log_debug(f"LlamaCppRunner: Error loading model: {e}")
            raise

    def stop(self):
        from promptperfector.logic.logger import log_debug
        log_debug("LlamaCppRunner.stop() called.")
        if self.llm:
            try:
                if hasattr(self.llm, 'close'):
                    log_debug("LlamaCppRunner: Calling llm.close().")
                    self.llm.close()
                elif hasattr(self.llm, '__del__'):
                    log_debug("LlamaCppRunner: Calling llm.__del__().")
                    self.llm.__del__()
            except Exception as e:
                log_debug(f"LlamaCppRunner: Exception during close: {e}")
        self.llm = None
        log_debug("LlamaCppRunner: Model set to None.")

    def prompt(self, prompt_text, max_tokens=64, stop=None):
        from promptperfector.logic.logger import log_debug
        import time
        log_debug(f"LlamaCppRunner.prompt() called. Prompt: {prompt_text!r}, max_tokens: {max_tokens}, stop: {stop}, n_ctx={self.n_ctx}, n_threads={self.n_threads}")
        if not self.llm:
            log_debug("LlamaCppRunner: Model not started!")
            raise RuntimeError('llama-cpp-python model not started')
        try:
            t0 = time.perf_counter()
            output = self.llm(prompt_text, max_tokens=max_tokens, stop=stop or ["\n"])
            t1 = time.perf_counter()
            log_debug(f"LlamaCppRunner: Model output: {output}")
            log_debug(f"LlamaCppRunner: Prompt completed in {t1-t0:.2f} seconds.")
            return output["choices"][0]["text"]
        except Exception as e:
            log_debug(f"LlamaCppRunner: Exception during prompt: {e}")
            raise
