import uvicorn


def main() -> None:
    uvicorn.run("novellia_takehome.api:app", reload=True)
