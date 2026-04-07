import asyncio, sys
sys.path.append('backend')
from database.connection import Database
from controllers.projeto_controller import buscar_projetos_controller

async def main():
    await Database.connect()
    r = await buscar_projetos_controller()
    print(r)

asyncio.run(main())
