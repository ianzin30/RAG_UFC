"""Teste de conexão e resposta dos três modelos da Spark (sequencial, sem dados reais)."""
import sys
import time

from llm_client import (DEFAULT_MODEL, LLMClient, LLMError, LLMAuthenticationError,
                        LLMConnectionError)

MODELS = (DEFAULT_MODEL, 'openai/gpt-oss-20b', 'Qwen/Qwen2.5-7B-Instruct-AWQ')


def main():
    failed = False
    try:
        with LLMClient() as client:
            available = client.list_models()
            for model_id in available:
                print(model_id)
            for model in MODELS:
                if model not in available:
                    print(f'{model} | ERRO: modelo não anunciado pela API', file=sys.stderr)
                    failed = True
                    continue
                params = {'temperature': 0, 'seed': 42, 'max_tokens': 2048}
                if model == DEFAULT_MODEL:
                    params.update(max_tokens=128, extra_body={'chat_template_kwargs': {'enable_thinking': False}})
                elif model == 'Qwen/Qwen2.5-7B-Instruct-AWQ':
                    params['max_tokens'] = 64
                started = time.perf_counter()
                try:
                    reply = client.chat([{'role': 'user', 'content': 'Responda apenas: pong'}], model=model, **params)
                except (LLMAuthenticationError, LLMConnectionError):
                    raise  # Stop rather than sending more requests with invalid auth/connectivity.
                except LLMError as exc:
                    print(f'{model} | ERRO: {exc} | {time.perf_counter() - started:.2f} s', file=sys.stderr)
                    failed = True
                    continue
                print(f'{model} | {reply.strip()} | {time.perf_counter() - started:.2f} s')
                if reply.strip().lower() != 'pong':
                    print(f'{model} | ERRO: resposta diferente de pong', file=sys.stderr)
                    failed = True
    except LLMError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
