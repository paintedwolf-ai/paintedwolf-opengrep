from fastapi import FastAPI, Path

app = FastAPI()

@app.get("/files/{name}")
def files(name: str = Path(...)):
    sink("safe")


def singleton():
    value = ...
    sink(value)
    dirty = source()
    dirty = ...
    sink(dirty)
    # ruleid: flow
    sink(transform(source(), ...))
