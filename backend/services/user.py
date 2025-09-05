from repositories.db.user import UserRepository
class UserService:
    def __init__(self):
        self.repository = UserRepository()
    
    async def put_user(self, json):
        await self.repository.put_user(json=json)
    
    async def get_json_by_id(self, id):
        await self.repository.get_json_by_id(user_id=id)