import requests
import json
import logging
import streamlit as st
from typing import List, Dict, Any, Generator, Optional

logger = logging.getLogger("safety_ai.api_client")

class SafetyAIAPIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:5000/api/v1"):
        self.base_url = base_url

    def _get_headers(self, content_type="application/json"):
        # Em uma integração real, pegamos o token do st.session_state (Firebase Auth)
        token = st.session_state.get("firebase_token", "")
        headers = {
            "Authorization": f"Bearer {token}"
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def list_knowledge(self) -> List[Dict]:
        """Lista documentos ativos na base de conhecimento (usuário)."""
        url = f"{self.base_url}/documents/knowledge"
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao listar conhecimento: {e}")
            return []

    def admin_list_knowledge(self) -> List[Dict]:
        """Lista todos os documentos da base (Admin)."""
        url = f"{self.base_url}/admin/knowledge"
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao listar conhecimento (Admin): {e}")
            return []

    def admin_upload_knowledge(self, file, title: str, category: str, description: str = "") -> Dict:
        """Faz upload de um documento para a base curada (Admin)."""
        url = f"{self.base_url}/admin/knowledge/upload"
        files = {"file": (file.name, file.getvalue(), file.type)}
        data = {
            "title": title,
            "category": category,
            "description": description
        }
        try:
            # Ao enviar arquivos com 'files', o requests cuida do Content-Type (multipart)
            response = requests.post(url, data=data, files=files, headers=self._get_headers(content_type=None))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro no upload administrativo: {e}")
            return {"status": "error", "message": str(e)}

    def admin_delete_knowledge(self, doc_id: str) -> bool:
        """Deleta um documento da base (Admin)."""
        url = f"{self.base_url}/admin/knowledge/{doc_id}"
        try:
            response = requests.delete(url, headers=self._get_headers())
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar conhecimento: {e}")
            return False

    def admin_toggle_knowledge(self, doc_id: str) -> Dict:
        """Alterna status ativo/inativo de um documento (Admin)."""
        url = f"{self.base_url}/admin/knowledge/{doc_id}/toggle"
        try:
            response = requests.patch(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao alternar status: {e}")
            return {}

    def ask(self, query: str, history: List[Dict] = None, attached_docs: List[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/ask"
        payload = {
            "query": query,
            "history": history or [],
            "attached_docs": attached_docs or [],
            "stream": False
        }
        try:
            response = requests.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao chamar API (ask): {e}")
            return {"answer": f"Erro de conexão com o servidor de IA: {e}", "sources": []}

    def stream_ask(self, query: str, history: List[Dict] = None, attached_docs: List[str] = None) -> Generator[str, None, None]:
        url = f"{self.base_url}/chat/stream"
        payload = {
            "query": query,
            "history": history or [],
            "attached_docs": attached_docs or [],
            "stream": True
        }
        
        self.last_metadata = {}
        
        try:
            import httpx
            with httpx.stream("POST", url, json=payload, headers=self._get_headers(), timeout=None) as r:
                current_event = None
                for line in r.iter_lines():
                    if line.startswith("event: "):
                        current_event = line[7:].strip()
                    elif line.startswith("data: "):
                        data = line[6:].strip()
                        
                        if data == "[DONE]":
                            break
                            
                        if current_event == "metadata":
                            try:
                                self.last_metadata = json.loads(data)
                            except:
                                pass
                        elif current_event == "error":
                            yield f"Erro na API: {data}"
                        else:
                            # Default event (message)
                            yield data
                        
                        # Reset event unless it's a multi-line data for the same event
                        # But SSE usually sends event once per data block
                        current_event = None
        except Exception as e:
            logger.error(f"Erro no streaming da API: {e}")
            yield f"Erro de conexão: {e}"

    def get_last_suggested_downloads(self) -> List[Dict]:
        return self.last_metadata.get("suggested_downloads", [])

    def generate_document(self, doc_type: str, data: Dict[str, Any], user_logo_base64: Optional[str] = None) -> Optional[bytes]:
        url = f"{self.base_url}/documents/generate/{doc_type}"
        payload = {
            "data": data,
            "user_logo_base64": user_logo_base64
        }
        try:
            response = requests.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Erro ao gerar documento via API ({doc_type}): {e}")
            return None
