import asyncio
from api.routers.extraction import run_extraction
from pydantic import BaseModel

class RunExtractionReq(BaseModel):
    project_id: int

async def main():
    req = RunExtractionReq(project_id=1110001)
    current_user = {"id": 1}
    
    resp = await run_extraction(req, current_user)
    
    async for chunk in resp.body_iterator:
        try:
            print(chunk.decode('utf-8').strip())
        except:
            print(chunk)

if __name__ == "__main__":
    asyncio.run(main())
