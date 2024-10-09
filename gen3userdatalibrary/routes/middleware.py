from fastapi import Request, FastAPI, HTTPException

app = FastAPI()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != "Bearer yoursecrettoken":
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Continue processing the request
    response = await call_next(request)
    return response
