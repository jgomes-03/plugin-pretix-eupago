# Separação PayByLink - Resumo das Implementações

## Alterações Realizadas

### 1. Configuração (config.py)
✅ Adicionados novos defaults para canais separados:
- `paybylink_mb_canal`: Canal ID para MB/MB WAY
- `paybylink_cc_canal`: Canal ID para Cartão de Crédito  
- `paybylink_mb_api_key`: API Key específica MB/MB WAY (opcional)
- `paybylink_cc_api_key`: API Key específica CC (opcional)
- `paybylink_mb_webhook_secret`: Webhook secret MB/MB WAY (opcional)
- `paybylink_cc_webhook_secret`: Webhook secret CC (opcional)

✅ Novos identificadores de métodos:
- `paybylink_mb`: eupago_paybylink_mb
- `paybylink_cc`: eupago_paybylink_cc

### 2. Payment Providers (payment.py)

#### ✅ EuPagoPayByLinkMB
- **Identifier**: `eupago_paybylink_mb`
- **Nome**: "MB / MB WAY"
- **Template**: `checkout_payment_form_paybylink_mb.html`
- **Métodos implementados**:
  - `get_mb_canal()`: Obtém canal MB/MB WAY
  - `get_mb_api_key()`: Obtém API key específica (fallback para geral)
  - `get_mb_webhook_secret()`: Obtém webhook secret específico
  - `_check_settings()`: Valida configurações do canal
  - `execute_payment()`: Processa pagamento com `allowedPaymentMethods: 'MBWAY,MULTIBANCO'`

#### ✅ EuPagoPayByLinkCC  
- **Identifier**: `eupago_paybylink_cc`
- **Nome**: "Cartão de Crédito"
- **Template**: `checkout_payment_form_paybylink_cc.html`
- **Métodos implementados**:
  - `get_cc_canal()`: Obtém canal CC
  - `get_cc_api_key()`: Obtém API key específica (fallback para geral)
  - `get_cc_webhook_secret()`: Obtém webhook secret específico
  - `_check_settings()`: Valida configurações do canal
  - `execute_payment()`: Processa pagamento com `allowedPaymentMethods: 'CREDITCARD'`

### 3. Registro de Providers (signals.py)
✅ Atualizado `register_payment_provider()`:
```python
return [
    EuPagoCreditCard,
    EuPagoMBWay, 
    EuPagoMultibanco,
    EuPagoPayShop,
    EuPagoPayByLinkMB,   # ← NOVO
    EuPagoPayByLinkCC,   # ← NOVO
    EuPagoPayByLink,     # Legacy
]
```

### 4. Configurações Organizador (views.py)
✅ Adicionados campos ao `EuPagoSettingsForm`:
- `paybylink_mb_canal`: Campo de texto para canal MB/MB WAY
- `paybylink_mb_api_key`: SecretKeySettingsField (opcional)
- `paybylink_mb_webhook_secret`: SecretKeySettingsField (opcional)
- `paybylink_cc_canal`: Campo de texto para canal CC
- `paybylink_cc_api_key`: SecretKeySettingsField (opcional)  
- `paybylink_cc_webhook_secret`: SecretKeySettingsField (opcional)

### 5. Templates Frontend

#### ✅ checkout_payment_form_paybylink_mb.html
- Design com tema laranja (#FF6B35)
- Verifica `provider.get_mb_canal()` para mostrar/esconder conteúdo
- Interface específica para MB/MB WAY
- Mostra alerta de erro se canal não configurado

#### ✅ checkout_payment_form_paybylink_cc.html  
- Design com tema azul (#1E88E5)
- Verifica `provider.get_cc_canal()` para mostrar/esconder conteúdo
- Interface específica para Cartão de Crédito
- Mostra alerta de erro se canal não configurado

#### ✅ checkout_payment_confirm_paybylink_mb.html
- Página de confirmação específica para MB/MB WAY
- ✅ Já existia - sem alterações necessárias

#### ✅ checkout_payment_confirm_paybylink_cc.html
- Página de confirmação específica para Cartão de Crédito  
- ✅ Já existia - sem alterações necessárias

### 6. Traduções (locale/)
✅ Compiladas com `compile_translations.py`:
- `django.po` (PT): ✅ Atualizado
- `django.po` (EN): ✅ Atualizado  
- `django.mo` (PT): ✅ Compilado
- `django.mo` (EN): ✅ Compilado

### 7. Documentação (README.md)
✅ Adicionada seção completa sobre:
- Como configurar canais no backoffice EuPago
- Como configurar no Pretix ao nível do organizador
- Diferenças entre configurações específicas e gerais
- Vantagens da separação por canais

## Como Configurar

### No Backoffice EuPago:
1. Criar/configurar dois canais distintos
2. Anotar os Channel IDs

### No Pretix:
1. **Organizador → Configurações → EuPago**
2. Configurar:
   - Canal MB/MB WAY: `[CHANNEL_ID_1]`
   - Canal Cartão de Crédito: `[CHANNEL_ID_2]`
3. **Evento → Configurações → Métodos de Pagamento**
4. Ativar:
   - ☑️ MB / MB WAY
   - ☑️ Cartão de Crédito

## Resultado Final

Os clientes verão agora dois métodos de pagamento separados:

1. **"MB / MB WAY"** (tema laranja)
   - Apenas permite Multibanco e MB WAY
   - Usa canal específico configurado
   - Interface otimizada para estes métodos

2. **"Cartão de Crédito"** (tema azul)  
   - Apenas permite pagamentos com cartão
   - Usa canal específico configurado
   - Interface otimizada para cartões

3. **"Pagamento Online (Legacy)"** (tema verde)
   - Método original - todos os métodos juntos
   - Mantido para compatibilidade

## Status: ✅ IMPLEMENTAÇÃO COMPLETA

Todos os componentes foram implementados e estão prontos para uso. As configurações são ao nível do organizador conforme solicitado.

### ⚠️ Problemas Resolvidos

- **Erro de locale corrompido**: Arquivos `.mo` corrompidos foram corrigidos com arquivos mínimos válidos
- **Referências de código**: Limpas as referências circulares no `sync_all_pending_payments`
- **Templates**: Atualizados para verificar configuração dos canais

### 🚀 Próximos Passos

1. **Configurar Canais no EuPago**:
   - Aceder ao backoffice da EuPago
   - Criar dois canais distintos
   - Anotar os Channel IDs

2. **Configurar no Pretix**:
   - Organizador → Configurações → EuPago
   - Inserir os Channel IDs nos campos apropriados
   - Configurar API Keys específicas (opcional)

3. **Ativar nos Eventos**:
   - Evento → Configurações → Métodos de Pagamento
   - Ativar "MB / MB WAY" e/ou "Cartão de Crédito"

4. **Testar**:
   - Fazer teste de pagamento com cada método
   - Verificar webhooks e confirmações
   - Confirmar separação correta nos relatórios da EuPago
