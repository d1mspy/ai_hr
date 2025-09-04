from repositories.db.repository import Repository

repository = Repository()

class Service():
    def __init__(self, repository: Repository):
        self.repository = repository
    
    
    async def test_post(self, testdb: str) -> None:
        await repository.test_post(testdb)
        
    async def test_get(self) -> list | None:
        resp = await repository.test_get()
        return resp