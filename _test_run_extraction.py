import asyncio
from api.routers.extraction import run_extraction
from pydantic import BaseModel

class Req(BaseModel):
    project_id: int
    force_reextract: bool = False

async def main():
    req = Req(project_id=1590001, force_reextract=True)
    async for msg in run_extraction(req, {'id': 1}):
        print(msg)

if __name__ == "__main__":
    asyncio.run(main())
