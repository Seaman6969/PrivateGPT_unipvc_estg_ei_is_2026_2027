import threading


def run_async(root, work_fn, done_fn) -> None:
    thread = threading.Thread(target=_worker, args=(root, work_fn, done_fn))
    thread.daemon = True
    thread.start()


def _worker(root, work_fn, done_fn) -> None:
    result = _safe_call(work_fn)
    root.after(0, done_fn, result)


def _safe_call(fn):
    try:
        return fn()
    except Exception as e:
        return e
