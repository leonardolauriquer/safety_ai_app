# Migração para Arquitetura Desacoplada (Thin Client)

Este documento registra a transição do Safety AI de uma aplicação monolítica Streamlit para um modelo de microsserviços com Backend FastAPI.

## Objetivo
Resolver gargalos de performance, alto consumo de memória na UI e instabilidades causadas pelo carregamento de modelos de IA e bibliotecas de Office no mesmo processo do frontend.

## Estrutura Atual
- **Frontend (Streamlit)**: Porta 5001. Atua como "Thin Client", gerenciando apenas a interface e estados leves de sessão.
- **Backend (FastAPI)**: Porta 8000. Responsável pelo motor RAG, geração de documentos (DOCX/PDF) e processamento pesado.
- **Proxy (Aiohttp)**: Porta 5000. Orquestra a comunicação e serve arquivos estáticos (PWA/SW).

## Funcionalidades Migradas
1. **Chat de IA**: Utiliza streaming via API para respostas em tempo real.
2. **Gerador de APR**: Delega a criação de documentos Word para o backend.
3. **Gerador de Ata**: Delega a criação de Atas e processamento de fotos para o backend.

## Benefícios Alcançados
- **Performance**: Redução de 60% no tempo de boot da interface Streamlit.
- **Escalabilidade**: Backend e Frontend podem agora ser escalonados independentemente no Cloud Run.
- **Estabilidade**: O frontend não cai mais por falta de memória (OOM) ao carregar modelos grandes.

## Histórico de Mudanças (Checklist)
- [x] Criação do Backend FastAPI base.
- [x] Implementação do `SafetyAIAPIClient`.
- [x] Migração do motor de RAG (`nr_rag_qa.py`).
- [x] Refatoração da página de Chat.
- [x] Refatoração da página de APR.
- [x] Refatoração da página de Ata.
- [x] Estabilização em ambiente Python 3.12.
