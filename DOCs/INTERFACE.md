# Sistema de Interface e Design

## Visao Geral

O SafetyAI utiliza um design system chamado "Cyber-Neon" que combina elementos futuristas com usabilidade profissional.

---

## 1. Paleta de Cores

### 1.1 Cores Base (Espaco Profundo)

| Nome | Hex | Uso |
|------|-----|-----|
| Void Black | `#020617` | Fundo principal |
| Space Blue | `#0B1220` | Fundo secundario |
| Nebula | `#0F172A` | Cards e containers |
| Deep Space | `#1E293B` | Bordas e divisores |

### 1.2 Cores Neon (Acentos)

| Nome | Hex | Uso |
|------|-----|-----|
| Neon Green | `#4ADE80` | Sucesso, destaque principal |
| Neon Cyan | `#22D3EE` | Links, acoes secundarias |
| Neon Orange | `#F97316` | Alertas, atencao |
| Neon Purple | `#A855F7` | Informacoes especiais |
| Neon Pink | `#EC4899` | Destaques premium |

### 1.3 Cores de Texto

| Nome | Hex | Uso |
|------|-----|-----|
| White | `#FFFFFF` | Texto principal |
| Light Gray | `#94A3B8` | Texto secundario |
| Muted | `#64748B` | Texto desabilitado |

---

## 2. Tipografia

### 2.1 Fontes

| Tipo | Fonte | Uso |
|------|-------|-----|
| Display | Orbitron | Titulos, logos |
| Body | Inter | Texto corrido, UI |
| Mono | JetBrains Mono | Codigo, dados |

### 2.2 Tamanhos

```css
--font-xs: 0.75rem;   /* 12px */
--font-sm: 0.875rem;  /* 14px */
--font-base: 1rem;    /* 16px */
--font-lg: 1.125rem;  /* 18px */
--font-xl: 1.25rem;   /* 20px */
--font-2xl: 1.5rem;   /* 24px */
--font-3xl: 1.875rem; /* 30px */
```

---

## 3. Efeitos Visuais

### 3.1 Glassmorphism

```css
.glass-card {
    background: rgba(15, 23, 42, 0.7);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(74, 222, 128, 0.2);
    border-radius: 16px;
}
```

### 3.2 Neon Glow

```css
.neon-glow {
    box-shadow: 
        0 0 5px rgba(74, 222, 128, 0.3),
        0 0 10px rgba(74, 222, 128, 0.2),
        0 0 20px rgba(74, 222, 128, 0.1);
}

.neon-glow-hover:hover {
    box-shadow: 
        0 0 10px rgba(74, 222, 128, 0.5),
        0 0 20px rgba(74, 222, 128, 0.3),
        0 0 40px rgba(74, 222, 128, 0.2);
}
```

### 3.3 Gradientes

```css
/* Gradiente de fundo animado */
.cyber-gradient {
    background: linear-gradient(
        135deg,
        #020617 0%,
        #0B1220 50%,
        #0F172A 100%
    );
}

/* Gradiente neon para botoes */
.neon-button-gradient {
    background: linear-gradient(
        90deg,
        #4ADE80 0%,
        #22D3EE 100%
    );
}
```

---

## 4. Componentes UI

### 4.1 Arquivo: `theme_config.py`

### 4.2 Dicionario THEME

```python
THEME = {
    'colors': {
        'primary': '#4ADE80',
        'secondary': '#22D3EE',
        'background': '#020617',
        'surface': '#0F172A',
        'text': '#FFFFFF',
        'text_muted': '#94A3B8',
        'success': '#4ADE80',
        'warning': '#F97316',
        'error': '#EF4444',
    },
    'icons': {
        'check': '<svg>...</svg>',
        'error_x': '<svg>...</svg>',
        'warning': '<svg>...</svg>',
        # ... mais icones
    },
    'fonts': {
        'display': 'Orbitron',
        'body': 'Inter',
    }
}
```

### 4.3 Funcoes Utilitarias

```python
def get_icon(icon_name: str) -> str:
    """Retorna SVG do icone pelo nome"""

def render_hero_section(title: str, subtitle: str) -> None:
    """Renderiza secao hero com estilo cyber-neon"""

def render_feature_card(icon: str, title: str, description: str) -> None:
    """Renderiza card de feature com glassmorphism"""
```

---

## 5. Icones (Tabler Icons)

### 5.1 Formato

Icones sao SVGs inline para garantir carregamento confiavel:

```python
ICONS = {
    'check': '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" 
                viewBox="0 0 24 24" fill="none" stroke="currentColor" 
                stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20,6 9,17 4,12"></polyline></svg>''',
    
    'calendar': '''<svg>...</svg>''',
    'chat': '''<svg>...</svg>''',
    # ... mais icones
}
```

### 5.2 Icones Disponiveis

| Nome | Uso |
|------|-----|
| `check` | Sucesso, confirmacao |
| `error_x` | Erro, fechar |
| `warning` | Alerta |
| `info` | Informacao |
| `calendar` | Datas, cronograma |
| `chat` | Chat, mensagens |
| `document` | Documentos |
| `calculator` | Calculos |
| `search` | Busca |
| `settings` | Configuracoes |
| `user` | Usuario, perfil |
| `folder` | Pastas, arquivos |
| `download` | Download |
| `upload` | Upload |

---

## 6. Pagina de Login

### 6.1 Layout Responsivo

```css
/* Desktop */
.login-container {
    max-width: 500px;
    padding: 2rem;
}

/* Tablet */
@media (max-width: 768px) {
    .login-container {
        max-width: 90%;
        padding: 1.5rem;
    }
}

/* Mobile (altura pequena) */
@media (max-height: 650px) {
    .login-logo { height: 80px; }
    .features-list { display: none; }
}
```

### 6.2 Componentes

1. **Logo**: SVG com glow neon
2. **Titulo**: "SafetyAI" em Orbitron
3. **Subtitulo**: Descricao do app
4. **Features**: Lista de recursos com checkmarks
5. **Botao Google**: Glassmorphism com hover effect

---

## 7. Sidebar de Navegacao

### 7.1 Estrutura

```python
MENU_ITEMS = [
    {"icon": "home", "label": "Inicio", "page": "home"},
    {"icon": "chat", "label": "Chat IA", "page": "chat"},
    {"icon": "search", "label": "Consultas", "page": "quick_queries"},
    {"icon": "calculator", "label": "Dimensionamentos", "page": "sizing"},
    {"icon": "document", "label": "Documentos", "page": "documents"},
    {"icon": "folder", "label": "Biblioteca", "page": "library"},
    {"icon": "gamepad", "label": "Jogos", "page": "games"},
    {"icon": "settings", "label": "Configuracoes", "page": "settings"},
]
```

### 7.2 Estilos

```css
.sidebar-item {
    padding: 0.75rem 1rem;
    border-radius: 8px;
    transition: all 0.2s ease;
}

.sidebar-item:hover {
    background: rgba(74, 222, 128, 0.1);
}

.sidebar-item.active {
    background: rgba(74, 222, 128, 0.2);
    border-left: 3px solid #4ADE80;
}
```

---

## 8. Cards e Containers

### 8.1 Card Padrao

```css
.card {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(74, 222, 128, 0.15);
    border-radius: 12px;
    padding: 1.5rem;
}
```

### 8.2 Card Hover

```css
.card-hover {
    transition: all 0.3s ease;
}

.card-hover:hover {
    transform: translateY(-2px);
    box-shadow: 0 0 20px rgba(74, 222, 128, 0.2);
    border-color: rgba(74, 222, 128, 0.4);
}
```

---

## 9. Botoes

### 9.1 Botao Primario (Neon)

```css
.btn-primary {
    background: linear-gradient(90deg, #4ADE80, #22D3EE);
    color: #020617;
    font-weight: 600;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    border: none;
    transition: all 0.3s ease;
}

.btn-primary:hover {
    box-shadow: 0 0 20px rgba(74, 222, 128, 0.5);
    transform: scale(1.02);
}
```

### 9.2 Botao Secundario (Outline)

```css
.btn-secondary {
    background: transparent;
    color: #4ADE80;
    border: 1px solid #4ADE80;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
}

.btn-secondary:hover {
    background: rgba(74, 222, 128, 0.1);
}
```

---

## 10. Animacoes

### 10.1 Fade In

```css
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.fade-in {
    animation: fadeIn 0.3s ease-out;
}
```

### 10.2 Pulse Neon

```css
@keyframes pulseNeon {
    0%, 100% { box-shadow: 0 0 5px rgba(74, 222, 128, 0.3); }
    50% { box-shadow: 0 0 20px rgba(74, 222, 128, 0.5); }
}

.pulse-neon {
    animation: pulseNeon 2s infinite;
}
```

---

## 11. Responsividade

### 11.1 Breakpoints

| Nome | Largura | Uso |
|------|---------|-----|
| Mobile | < 640px | Smartphones |
| Tablet | 640px - 1024px | Tablets |
| Desktop | > 1024px | Computadores |

### 11.2 Media Queries por Altura

```css
/* Telas muito baixas */
@media (max-height: 800px) { /* Ajustes */ }
@media (max-height: 650px) { /* Esconde elementos */ }
```
