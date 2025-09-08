from repositories.db.user import UserRepository
from utils.encrypt_id import encrypt_user_id, decrypt_user_id
class UserService:
    def __init__(self):
        self.repository = UserRepository()
    
    async def put_user(self, json):
        await self.repository.put_user(json=json)
    
    async def get_json_by_id(self, id):
        return await self.repository.get_json_by_id(user_id=id)
    
    async def get_encrypted_id(self, id):
        return await encrypt_user_id(user_id=id)
    
    async def validate_user(self, id)->int:
        id = await decrypt_user_id(token=id)
        if await self.repository.check_user(user_id=id):
            return id
        else:
            return None
        
    async def check_user(self, id)-> bool:
        return await self.repository.check_user(user_id=id)