"""
Módulo de validação e sanitização de inputs para o SafetyAI App.

Este módulo fornece funções para validar e sanitizar entradas do usuário,
prevenindo erros de processamento e potenciais vulnerabilidades de segurança.
"""

import re
import html
from datetime import date, datetime
from typing import Tuple, Optional, Any


def validate_cnae(cnae: str) -> Tuple[bool, str, Optional[str]]:
    """
    Valida e limpa um código CNAE.
    
    Args:
        cnae: Código CNAE a ser validado
        
    Returns:
        Tuple contendo:
        - bool: Se o CNAE é válido
        - str: CNAE limpo (apenas dígitos)
        - Optional[str]: Mensagem de erro (None se válido)
    """
    if not cnae:
        return False, "", "O código CNAE é obrigatório."
    
    cleaned = re.sub(r'[\s.\-/]', '', str(cnae).strip())
    
    if not cleaned:
        return False, "", "O código CNAE é obrigatório."
    
    if not cleaned.isdigit():
        return False, "", "O código CNAE deve conter apenas números."
    
    if len(cleaned) < 5 or len(cleaned) > 7:
        return False, "", f"O código CNAE deve ter entre 5 e 7 dígitos. Encontrado: {len(cleaned)} dígitos."
    
    return True, cleaned, None


def validate_positive_integer(
    value: str, 
    field_name: str = "Valor",
    min_val: int = 0, 
    max_val: int = 1000000
) -> Tuple[bool, int, Optional[str]]:
    """
    Valida se o valor é um número inteiro positivo dentro do range especificado.
    
    Args:
        value: Valor a ser validado (string)
        field_name: Nome do campo para mensagens de erro
        min_val: Valor mínimo permitido
        max_val: Valor máximo permitido
        
    Returns:
        Tuple contendo:
        - bool: Se o valor é válido
        - int: Valor convertido para inteiro (0 se inválido)
        - Optional[str]: Mensagem de erro (None se válido)
    """
    if not value:
        return False, 0, f"{field_name} é obrigatório."
    
    cleaned = str(value).strip().replace(',', '').replace('.', '')
    
    try:
        parsed = int(cleaned)
    except ValueError:
        return False, 0, f"{field_name} deve ser um número inteiro válido."
    
    if parsed < min_val:
        return False, 0, f"{field_name} deve ser maior ou igual a {min_val}."
    
    if parsed > max_val:
        return False, 0, f"{field_name} deve ser menor ou igual a {max_val}."
    
    return True, parsed, None


def sanitize_text_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitiza entrada de texto removendo caracteres perigosos e limitando tamanho.
    
    Args:
        text: Texto a ser sanitizado
        max_length: Comprimento máximo permitido
        
    Returns:
        Texto sanitizado
    """
    if not text:
        return ""
    
    sanitized = str(text)
    
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\n\r\t')
    
    sanitized = html.escape(sanitized)
    
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()


def validate_date_input(
    date_value: Any,
    allow_past: bool = True,
    allow_future: bool = True,
    min_date: Optional[date] = None,
    max_date: Optional[date] = None
) -> Tuple[bool, Optional[date], Optional[str]]:
    """
    Valida uma entrada de data.
    
    Args:
        date_value: Valor de data a ser validado
        allow_past: Se datas passadas são permitidas
        allow_future: Se datas futuras são permitidas
        min_date: Data mínima permitida (opcional)
        max_date: Data máxima permitida (opcional)
        
    Returns:
        Tuple contendo:
        - bool: Se a data é válida
        - Optional[date]: Data validada (None se inválida)
        - Optional[str]: Mensagem de erro (None se válida)
    """
    if date_value is None:
        return False, None, "A data é obrigatória."
    
    if isinstance(date_value, datetime):
        date_value = date_value.date()
    elif isinstance(date_value, str):
        try:
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    date_value = datetime.strptime(date_value, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                return False, None, "Formato de data inválido. Use DD/MM/AAAA."
        except Exception:
            return False, None, "Não foi possível interpretar a data."
    elif not isinstance(date_value, date):
        return False, None, "Tipo de data inválido."
    
    today = date.today()
    
    if not allow_past and date_value < today:
        return False, None, "Datas passadas não são permitidas."
    
    if not allow_future and date_value > today:
        return False, None, "Datas futuras não são permitidas."
    
    if min_date and date_value < min_date:
        return False, None, f"A data deve ser a partir de {min_date.strftime('%d/%m/%Y')}."
    
    if max_date and date_value > max_date:
        return False, None, f"A data deve ser até {max_date.strftime('%d/%m/%Y')}."
    
    return True, date_value, None


def validate_email(email: str) -> Tuple[bool, str, Optional[str]]:
    """
    Valida um endereço de email.
    
    Args:
        email: Email a ser validado
        
    Returns:
        Tuple contendo:
        - bool: Se o email é válido
        - str: Email limpo
        - Optional[str]: Mensagem de erro (None se válido)
    """
    if not email:
        return False, "", "O email é obrigatório."
    
    cleaned = str(email).strip().lower()
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, cleaned):
        return False, "", "Formato de email inválido."
    
    return True, cleaned, None


def sanitize_markdown(text: str) -> str:
    """
    Sanitiza texto Markdown removendo padrões potencialmente perigosos.
    
    Args:
        text: Texto Markdown a ser sanitizado
        
    Returns:
        Texto Markdown sanitizado
    """
    if not text:
        return ""
    
    sanitized = str(text)
    
    sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'data:', 'data-disabled:', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'vbscript:', '', sanitized, flags=re.IGNORECASE)
    
    sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
    
    return sanitized
