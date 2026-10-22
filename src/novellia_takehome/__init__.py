import uvicorn


def main() -> None:
    """Run the API with uvicorn on localhost:8000, reloading on code changes."""
    uvicorn.run("novellia_takehome.api:app", reload=True)
