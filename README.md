# EuPago v2 Payment Provider for Pretix

Este plugin fornece integração completa com os métodos de pagamento EuPago v2 para o sistema Pretix, seguindo as melhores práticas e padrões do framework.

## Índice
- [Métodos de Pagamento Suportados](#métodos-de-pagamento-suportados)
- [Funcionalidades](#funcionalidades)
- [Detecção Automática de Status de Pagamento](#detecção-automática-de-status-de-pagamento)
- [Instalação](#instalação)
  - [Instalação Local](#instalação-local)
  - [Instalação em Container](#instalação-em-container)
- [Configuração](#configuração)
- [MBWay - Experiência de Usuário Aprimorada](#mbway---experiência-de-usuário-aprimorada)
- [Arquitetura de Webhooks](#arquitetura-de-webhooks)
- [Monitoramento e Depuração](#monitoramento-e-depuração)
- [Fluxo de Pagamento](#fluxo-de-pagamento)
- [Changelog](#changelog)
- [Licença](#licença)

## Métodos de Pagamento Suportados

- **Credit Card payments** - Pagamentos diretos com cartão através da EuPago
- **MBWay** - Método de pagamento móvel popular em Portugal  
- **Multibanco** - Referências Multibanco tradicionais para transferência bancária
- **PayShop** - Pagamentos em dinheiro através da rede PayShop

## Funcionalidades

- ✅ **Multi-method support** - All 4 EuPago payment methods
- ✅ **Real-time webhooks** - Automatic payment status detection and updates
- ✅ **MBWay Timer Page** - Interactive 5-minute countdown with real-time status polling
- ✅ **API status polling** - Backup mechanism for missed webhooks
- ✅ **Sandbox/Production** - Full testing environment support
- ✅ **Error handling** - Comprehensive error management and logging
- ✅ **Security** - Webhook signature validation and secure processing
- ✅ **Monitoring tools** - Management commands for payment status checking
- ✅ **Mobile-responsive** - Optimized for mobile payments
- ✅ **Internationalization** - Multi-language support (PT/EN)

## Detecção Automática de Status de Pagamento

Este plugin detecta automaticamente quando os pagamentos são concluídos e atualiza seu status no pretix usando:

### Método Primário: Webhooks
- **Notificações em tempo real** da EuPago quando o status do pagamento muda
- **Atualizações imediatas** - status de pagamento atualizado segundos após a conclusão
- **Validação segura** usando verificação de assinatura HMAC-SHA256
- **Todos os métodos de pagamento suportados** (MBWay, Credit Card, Multibanco, PayShop)

### Método de Backup: API Polling  
- **Mecanismo de fallback** para webhooks perdidos
- **Comandos de gerenciamento** para verificação do status de pagamento
- **Monitoramento automatizado** via cron jobs (opcional)
- **Verificação manual de status** para solução de problemas

## Instalação

### Instalação Local

1. Clone ou copie o plugin para o diretório de plugins Pretix:
```bash
# Navegue até o diretório de plugins Pretix
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

### Instalação em Container

Se você estiver usando o Pretix em um ambiente Docker:

1. Adicione o plugin ao seu `Dockerfile` personalizado:
```Dockerfile
FROM pretix/standalone:latest
USER root
WORKDIR /pretix/src
RUN pip3 install pretix-eupago-v2==2.0.0
USER pretixuser
```

2. Reconstrua e reinicie seus containers:
```bash
docker-compose build
docker-compose up -d
```

Ou usando o script de instalação:

```bash
# Usar o script install.sh para instalação automatizada
./install.sh production
```

## Configuração

### Configurações Obrigatórias
- **API Key** - Sua chave de API EuPago
- **Endpoint** - Escolha sandbox (teste) ou live (produção)

### Configurações Opcionais
- **Webhook Secret** - Para segurança aprimorada (recomendado para produção)
- **Client ID/Secret** - Se estiver usando autenticação OAuth

### Configuração de Webhook
Os webhooks são configurados automaticamente quando os pagamentos são criados. Não é necessária configuração manual de webhook!

**Formato da URL do Webhook**: `https://yourdomain.com/yourevent/eupago/webhook/`

## MBWay - Experiência de Usuário Aprimorada

O método de pagamento MBWay inclui uma **página de temporizador interativa** que proporciona uma excelente experiência ao usuário:

### 🎯 Recursos do Temporizador
- **Contagem regressiva de 5 minutos** com barra de progresso visual
- **Verificação de status em tempo real** a cada 3 segundos
- **Redirecionamento automático** quando o pagamento é confirmado
- **Interface otimizada para dispositivos móveis** perfeita para pagamentos por celular

### 📱 Fluxo do Usuário
1. Cliente seleciona MBWay e insere o número de telefone
2. **Redirecionado para página do temporizador** com contagem regressiva e instruções
3. Cliente recebe notificação MBWay no telefone
4. Cliente confirma pagamento no app MBWay
5. **Página detecta automaticamente** a confirmação e redireciona para o pedido

### 🔄 Detecção de Status
- **Primário**: Webhooks em tempo real da EuPago
- **Secundário**: Polling JavaScript a cada 3 segundos
- **Fallback**: Botões de verificação manual de status

## Arquitetura de Webhooks

### Abordagem Recomendada: Webhook Único e Global

**URL:** `https://seu-site.com/_eupago/webhook/`

#### Vantagens:
- **Simplicidade**: Uma única URL para configurar
- **Escalabilidade**: Funciona para múltiplos organizadores
- **Manutenção**: Mais fácil de gerir e debuggar
- **Conformidade**: Alinhado com as melhores práticas da EuPago

#### Como Funciona:
1. EuPago envia webhook para URL global
2. Plugin identifica o pagamento pelo `identifier` ou `reference`
3. Plugin encontra o organizador correto automaticamente
4. Processa o pagamento independentemente do evento/organizador

## Monitoramento e Depuração

### Comandos de Gerenciamento

Utilize os seguintes comandos para monitorar e verificar pagamentos:

```bash
# Verificar status de todos os pagamentos EuPago recentes
python manage.py eupago_check_payments

# Verificar status de um pagamento específico
python manage.py eupago_check_payment --reference REF123456
```

### Cron Jobs para Monitoramento Automático

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
4. EuPago notifica o Pretix via webhook sobre mudança de status
5. Plugin processa webhook e marca pagamento como completo
6. Cliente é redirecionado para página de sucesso

### Fluxo do Credit Card
1. Cliente seleciona pagamento por cartão de crédito
2. Cliente é redirecionado para página de pagamento segura da EuPago
3. Cliente insere dados do cartão e completa pagamento
4. EuPago processa o pagamento e notifica o Pretix
5. Cliente é redirecionado de volta ao Pretix

### Fluxo do MBWay
1. Cliente seleciona MBWay e insere número de telefone
2. Plugin cria solicitação MBWay via API EuPago
3. Cliente é redirecionado para página de temporizador
4. Cliente recebe notificação MBWay no telefone para aprovar
5. Após aprovação, EuPago envia webhook de confirmação
6. Cliente é automaticamente redirecionado para página de sucesso

### Fluxo do Multibanco/PayShop
1. Cliente seleciona método de pagamento
2. Plugin gera referência de pagamento via API EuPago
3. Referência é exibida para o cliente
4. Cliente completa pagamento (banco/PayShop)
5. EuPago detecta pagamento e notifica o Pretix via webhook
6. Pedido é marcado como pago

## Changelog

### v2.1.0
- Melhorias na página de temporizador MBWay
- Otimização da validação de webhook
- Correções de bugs no processamento de cartão de crédito

### v2.0.0
- Reescrita completa do plugin
- Suporte para todos os métodos de pagamento EuPago
- Implementação de webhook robusta
- Integração aprimorada com o Pretix

## Licença

Licenciado sob Apache Software License. Ver arquivo LICENSE para detalhes.
