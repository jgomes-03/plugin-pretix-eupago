# EuPago Integration Payment Provider - Pretix
## Versão 2.1

Este plugin fornece integração completa e moderna com os métodos de pagamento EuPago para o sistema Pretix, incluindo suporte completo para Webhooks 2.0 com encriptação AES-256-CBC e uma interface de utilizador melhorada.

## Índice
- [Métodos de Pagamento Suportados](#métodos-de-pagamento-suportados)
- [Funcionalidades](#funcionalidades)
- [Deteção Automática de Estado de Pagamento](#deteção-automática-de-estado-de-pagamento)
- [Instalação](#instalação)
  - [Instalação Local](#instalação-local)
  - [Instalação em Contentor](#instalação-em-contentor)
- [Configuração](#configuração)
- [MBWay - Experiência de Utilizador Melhorada](#mbway---experiência-de-utilizador-melhorada)
- [Arquitetura de Webhooks](#arquitetura-de-webhooks)
- [Monitorização e Depuração](#monitorização-e-depuração)
- [Fluxo de Pagamento](#fluxo-de-pagamento)
- [Registo de Alterações](#registo-de-alterações)
- [Licença](#licença)

## Métodos de Pagamento Suportados

- **Pagamentos com Cartão de Crédito** - Pagamentos diretos com cartão através da EuPago
- **MBWay** - Método de pagamento móvel popular em Portugal  
- **Multibanco** - Referências Multibanco tradicionais para transferência bancária
- **PayShop** - Pagamentos em numerário através da rede PayShop

## Funcionalidades

### ✨ **Novidades na v1.0**
- 🔐 **Webhooks 2.0 com Encriptação** - Suporte completo para webhooks encriptados AES-256-CBC
- 🎨 **Interface Moderna** - Templates redesenhados com melhor UX/UI
- 🧹 **Logs Otimizados** - Sistema de logging limpo e eficiente
- ✅ **Validação de Assinatura** - Implementação correta segundo documentação oficial EuPago
- 📱 **MBWay Melhorado** - Interface simplificada e mais responsiva

### 🚀 **Funcionalidades Principais**
- ✅ **Suporte multi-método** - Todos os 4 métodos de pagamento EuPago
- ✅ **Webhooks em tempo real** - Deteção e atualizações automáticas do estado de pagamento
- ✅ **Interface melhorada** - Templates modernos com melhor formatação e ícones
- ✅ **Consulta de estado API** - Mecanismo de reserva para webhooks perdidos
- ✅ **Sandbox/Produção** - Suporte completo ao ambiente de testes
- ✅ **Tratamento de erros** - Gestão e registo de erros abrangente
- ✅ **Segurança** - Validação de assinatura webhook e processamento seguro
- ✅ **Ferramentas de monitorização** - Comandos de gestão para verificação do estado de pagamento
- ✅ **Responsivo para dispositivos móveis** - Otimizado para pagamentos móveis
- ✅ **Internacionalização** - Suporte multi-idioma (PT/EN)

## Deteção Automática de Estado de Pagamento

Este plugin deteta automaticamente quando os pagamentos são concluídos e atualiza o seu estado no pretix utilizando:

### Método Primário: Webhooks
- **Notificações em tempo real** da EuPago quando o estado do pagamento muda
- **Atualizações imediatas** - estado de pagamento atualizado segundos após a conclusão
- **Validação segura** utilizando verificação de assinatura HMAC-SHA256 (implementação correta na v2.0.0)
- **Suporte completo para Webhooks 2.0** com encriptação AES-256-CBC
- **Todos os métodos de pagamento suportados** (MBWay, Cartão de Crédito, Multibanco, PayShop)

### Método de Reserva: Consulta API  
- **Mecanismo de reserva** para webhooks perdidos
- **Comandos de gestão** para verificação do estado de pagamento
- **Monitorização automatizada** via cron jobs (opcional)
- **Verificação manual do estado** para resolução de problemas

## Instalação

### Instalação Local

1. Clone ou copie o plugin para o diretório de plugins Pretix:
```bash
# Navegue até ao diretório de plugins Pretix
cd /path/to/pretix/src/pretix/plugins

# Clone ou copie o plugin eupago
cp -r /path/to/eupago ./

# Instale em modo de desenvolvimento
cd eupago
pip install -e .
```

2. Adicione o plugin à configuração do Pretix (`pretix.cfg`):
```ini
[pretix]
plugins = eupago

[locale]
timezone = Europe/Lisbon
```

3. Reinicie o servidor Pretix
```bash
# Reinicie o servidor
systemctl restart pretix-web pretix-worker
```

### Instalação em Contentor

Se estiver a utilizar o Pretix num ambiente Docker:

1. Adicione o plugin ao seu `Dockerfile` personalizado:
```Dockerfile
FROM pretix/standalone:latest
USER root
WORKDIR /pretix/src
RUN pip3 install pretix-eupago==1.1.0
USER pretixuser
```

2. Reconstrua e reinicie os seus contentores:
```bash
docker-compose build
docker-compose up -d
```

Ou utilizando o script de instalação:

```bash
# Usar o script install.sh para instalação automatizada
./install.sh production
```

## Configuração

### Configurações Obrigatórias
- **API Key** - Chave da API fornecida pela EuPago
- **Endpoint** - Escolha sandbox (teste) ou live (produção)

### Configurações Opcionais
- **Webhook Secret** - Para segurança melhorada (recomendado para produção)
  - O segredo deve ser configurado nas configurações do organizador como `payment_eupago_webhook_secret`
  - Alternativamente, pode ser definido como variável de ambiente `EUPAGO_WEBHOOK_SECRET`
- **Client ID/Secret** - Se estiver a utilizar autenticação OAuth

### Configuração de Webhook
Os webhooks são configurados automaticamente quando os pagamentos são criados. Não é necessária configuração manual de webhook!

**Formato da URL do Webhook**: `https://seudominio.com/seuevento/eupago/webhook/`

## MBWay - Experiência de Utilizador Melhorada

O método de pagamento MBWay inclui uma **página de temporizador interativa** que proporciona uma excelente experiência ao utilizador:

### 🎯 Funcionalidades do Temporizador
- **Contagem regressiva de 5 minutos** com barra de progresso visual
- **Verificação de estado em tempo real** a cada 3 segundos
- **Redirecionamento automático** quando o pagamento é confirmado
- **Interface otimizada para dispositivos móveis** perfeita para pagamentos por telemóvel

### 📱 Fluxo do Utilizador
1. Cliente seleciona MBWay e introduz o número de telemóvel
2. **É redirecionado para a página do temporizador** com contagem regressiva e instruções
3. Cliente recebe notificação MBWay no telemóvel
4. Cliente confirma pagamento na aplicação MBWay
5. **A página deteta automaticamente** a confirmação e redireciona para a encomenda

### 🔄 Deteção de Estado
- **Primário**: Webhooks em tempo real da EuPago
- **Secundário**: Consulta JavaScript a cada 3 segundos
- **Reserva**: Botões de verificação manual de estado

## Arquitetura de Webhooks

### Abordagem Recomendada: Webhook Único e Global

**URL:** `https://seu-site.com/_eupago/webhook/`

#### Vantagens:
- **Simplicidade**: Uma única URL para configurar
- **Escalabilidade**: Funciona para múltiplos organizadores
- **Manutenção**: Mais fácil de gerir e depurar
- **Conformidade**: Alinhado com as melhores práticas da EuPago

#### Como Funciona:
1. EuPago envia webhook para URL global
2. Plugin identifica o pagamento pelo `identifier` ou `reference`
3. Plugin encontra o organizador correto automaticamente
4. Processa o pagamento independentemente do evento/organizador

## Monitorização e Depuração

### Comandos de Gestão

Utilize os seguintes comandos para monitorizar e verificar pagamentos:

```bash
# Verificar estado de todos os pagamentos EuPago recentes
python manage.py eupago_check_payments

# Verificar estado de um pagamento específico
python manage.py eupago_check_payment --reference REF123456
```

### Cron Jobs para Monitorização Automática

Configure cron jobs para verificar automaticamente pagamentos pendentes:

```
# Exemplo de crontab - verificar pagamentos a cada 30 minutos
*/30 * * * * cd /path/to/pretix && python manage.py eupago_check_payments --status=pending
```

## Fluxo de Pagamento

### Fluxo Geral
1. Cliente seleciona método de pagamento EuPago
2. Plugin faz chamada à API da EuPago para criar pagamento
3. Cliente completa pagamento (depende do método)
4. EuPago notifica o Pretix via webhook sobre alteração de estado
5. Plugin processa webhook e marca pagamento como completo
6. Cliente é redirecionado para página de sucesso

### Fluxo do Cartão de Crédito
1. Cliente seleciona pagamento por cartão de crédito
2. Cliente é redirecionado para página de pagamento segura da EuPago
3. Cliente introduz dados do cartão e completa pagamento
4. EuPago processa o pagamento e notifica o Pretix
5. Cliente é redirecionado de volta ao Pretix

### Fluxo do MBWay
1. Cliente seleciona MBWay e introduz número de telemóvel
2. Plugin cria solicitação MBWay via API EuPago
3. Cliente é redirecionado para página de temporizador
4. Cliente recebe notificação MBWay no telemóvel para aprovar
5. Após aprovação, EuPago envia webhook de confirmação
6. Cliente é automaticamente redirecionado para página de sucesso

### Fluxo do Multibanco/PayShop
1. Cliente seleciona método de pagamento
2. Plugin gera referência de pagamento via API EuPago
3. Referência é apresentada ao cliente
4. Cliente completa pagamento (banco/PayShop)
5. EuPago deteta pagamento e notifica o Pretix via webhook
6. Encomenda é marcada como paga

## Registo de Alterações

### v1.0 - Interface Moderna e Webhooks 2.0 (Setembro 2025)
#### 🎨 **Melhorias de Interface**
- **Templates redesenhados** com interface moderna e ícones FontAwesome
- **Multibanco** - Referências com melhor formatação visual e códigos de cor
- **PayShop** - Layout otimizado com instruções passo-a-passo claras
- **MBWay** - Interface simplificada e mais responsiva
- **Mensagens melhoradas** - Alertas informativos e instruções mais claras

#### 🔐 **Webhooks 2.0 e Segurança**
- **Suporte completo Webhooks 2.0** - Encriptação AES-256-CBC
- **Validação de assinatura corrigida** - Implementação exata da documentação oficial EuPago
- **Decriptação automática** - Processamento seguro de payloads encriptados
- **Processamento melhorado** - Extração correta de dados de transação aninhados

#### 🧹 **Optimizações Técnicas**
- **Sistema de logging otimizado** - Remoção de logs verbosos desnecessários
- **Performance melhorada** - Código mais limpo e eficiente
- **Debugging inteligente** - Logs essenciais mantidos, ruído removido
- **Estabilidade aumentada** - Correções de bugs críticos

### v0.1 a v0.4 - Alpha
- Melhorias na página de temporizador MBWay
- Otimização da validação de webhook
- Correções de erros no processamento de cartão de crédito
- Renomeação de eupago_v2 para eupago
- Tradução da documentação para Português de Portugal

### Versões anteriores
- Reescrita completa do plugin
- Suporte para todos os métodos de pagamento EuPago
- Implementação de webhook robusta
- Integração melhorada com o Pretix

## Licença

Licenciado sob licença proprietária. Ver arquivo LICENSE para detalhes.

## Gestão de Versões

A versão do plugin é definida uma única vez no ficheiro `eupago/apps.py` na variável `__version__`. Quando atualizar a versão, execute o script `update_version.ps1` (Windows) ou `update_version.sh` (Linux/Mac) para sincronizar a versão em todos os ficheiros do projeto.

```bash
# Linux/Mac
./update_version.sh

# Windows
.\update_version.ps1
```

Este script atualiza a versão no README.md e outros ficheiros relevantes, e opcionalmente cria uma tag git com a nova versão.

## Setting up Webhook Security

For secure webhook processing, you should configure the webhook secret key. This can be done in two ways:

1. **Through Pretix Organizer Settings (Recommended)**
   - Go to Organizer Settings in the Pretix admin panel
   - Navigate to the EuPago plugin settings
   - Enter your webhook secret in the "Webhook Secret" field
   - Save your settings

2. **Using Environment Variables**
   - Set the environment variable `EUPAGO_WEBHOOK_SECRET` in your server configuration:
   ```bash
   export EUPAGO_WEBHOOK_SECRET='your_secret_here'
   ```

The webhook secret is used to:
- Validate webhook signature authentication
- Decrypt encrypted webhook data (when using EuPago Webhooks 2.0)

For maximum security, use a strong random string as your webhook secret. You should set the same secret in both your Pretix configuration and your EuPago account.
