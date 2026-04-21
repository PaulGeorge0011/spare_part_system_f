# services/wechat_service.py，企业微信集成服务
import json
import asyncio
from typing import Dict, Any, Optional
from wechatpy import WeChatClient
from wechatpy.exceptions import WeChatClientException
from app.core.config import settings
from app.core.cache import redis_client

class WeChatService:
    def __init__(self):
        self.corp_id = settings.WECHAT_CORP_ID
        self.corp_secret = settings.WECHAT_CORP_SECRET
        self.agent_id = settings.WECHAT_AGENT_ID
        self.client = WeChatClient(self.corp_id, self.corp_secret)
    
    async def get_access_token(self) -> str:
        """获取企业微信access_token"""
        cache_key = f"wechat:access_token:{self.corp_id}"
        
        # 尝试从缓存获取
        token = await redis_client.get(cache_key)
        if token:
            return token.decode('utf-8')
        
        # 从API获取
        try:
            self.client.fetch_access_token()
            token = self.client.access_token
            
            # 缓存token，有效期2小时
            await redis_client.setex(cache_key, 7200, token)
            return token
        except WeChatClientException as e:
            raise Exception(f"获取企业微信token失败: {e}")
    
    async def send_stock_alert(self, part_info: Dict, alert_type: str) -> bool:
        """发送库存预警消息"""
        try:
            token = await self.get_access_token()
            
            # 构建消息内容
            if alert_type == "low_stock":
                title = "库存预警: 低于最小库存"
                color = "warning"
            elif alert_type == "zero_stock":
                title = "紧急预警: 库存为零"
                color = "danger"
            else:
                title = "库存预警"
                color = "info"
            
            message = {
                "touser": "@all",  # 发送给所有人，可根据配置调整
                "msgtype": "textcard",
                "agentid": self.agent_id,
                "textcard": {
                    "title": title,
                    "description": (
                        f"备件名称: {part_info['name']}\n"
                        f"备件编号: {part_info['part_no']}\n"
                        f"当前库存: {part_info['stock_quantity']}\n"
                        f"最小库存: {part_info['min_quantity']}\n"
                        f"存放位置: {part_info['location']}"
                    ),
                    "url": f"{settings.FRONTEND_URL}/spare-parts/{part_info['id']}",
                    "btntxt": "查看详情"
                }
            }
            
            # 发送消息
            result = self.client.message.send_text_card(
                agent_id=self.agent_id,
                user_ids="@all",
                title=message['textcard']['title'],
                description=message['textcard']['description'],
                url=message['textcard']['url'],
                btntxt=message['textcard']['btntxt']
            )
            
            return result['errcode'] == 0
        except Exception as e:
            print(f"发送企业微信消息失败: {e}")
            return False
    
    async def get_user_info(self, code: str) -> Dict[str, Any]:
        """通过code获取用户信息"""
        try:
            user_info = self.client.get_oauth_user_info(code)
            return {
                "userid": user_info.get("UserId"),
                "name": user_info.get("name"),
                "department": user_info.get("department"),
                "avatar": user_info.get("avatar"),
                "email": user_info.get("email")
            }
        except WeChatClientException as e:
            raise Exception(f"获取用户信息失败: {e}")