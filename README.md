# Soluções

App para ERPNext (Frappe 15 e 16) com três módulos, cada um com sua própria página web:

| Módulo | Endereço | Para quem |
|---|---|---|
| [Portal do Cliente (Metrologia)](#portal-do-cliente-metrologia) | `/cliente`, `/consulta`, `/acesso` | Clientes do laboratório e equipe interna |
| [Central de TI](#central-de-ti) | `/ti` | Colaboradores e equipe de TI |
| [Fiscal: notas e boletos](#fiscal-notas-e-boletos) | `/fiscal` | Financeiro |

Instala e atualiza sem `bench migrate` nem `bench build`: o frontend compilado vai no próprio git ([veja abaixo](#instalação-e-atualização)).

---

## Portal do Cliente (Metrologia)

Portal para os clientes acompanharem calibração e manutenção dos seus equipamentos.

**O cliente consegue:**
- Ver os equipamentos com a situação da calibração (em dia, a vencer, vencida), o histórico e um QR Code por equipamento.
- Cadastrar equipamentos que não são calibrados aqui (calibrados por terceiros) e anexar o certificado externo.
- Consultar e baixar certificados, e registrar a análise crítica (aprovado ou reprovado, com observação).
- Acompanhar as ordens de serviço, solicitar serviço e aprovar ou recusar orçamentos.
- Registrar verificações intermediárias entre calibrações.
- Receber um resumo semanal por e-mail.

**Recursos de metrologia:**
- **Periodicidade inteligente** (ILAC-G24 / OIML D10): sugere o intervalo de calibração a partir do histórico (uso da tolerância e tendência de deriva).
- **Verificação intermediária**, com pontos e critério de aceitação.
- **Rastreabilidade**: os padrões usados em cada certificado, com download do certificado do padrão.

**Controle por distritos (opcional, por cliente):**
- O gestor do cliente vê todos os distritos.
- Cada usuário vê só os equipamentos do seu distrito.
- O próprio gestor cuida de distritos, usuários e distribuição de equipamentos.

**Equipe interna:**
- **Central do portal**: num lugar só, liga cliente, contatos, acesso ao portal, distritos, usuários, equipamentos e OS. Há atalho no formulário do Cliente.
- **`/consulta`**: painel operacional, relatórios com exportação, histórico de atendimento e logs de auditoria de quem acessou e alterou o quê.
- **`/acesso`**: entrada do portal, com recuperação de senha que não revela quem tem acesso.

**Integração:** o portal lê os dados por um *adapter* (`solucoes/portal/adapters`). O `padrao.py` usa os DocTypes deste app; o `er.py` usa os DocTypes da empresa (Equipamentos e Ordem Servico Interna/Externa).

---

## Central de TI

Chamados, patrimônio e gestão de TI, pensados para uma equipe pequena e integrados ao ERP.

**Chamados:**
- O colaborador abre o chamado pela página (colando prints com Ctrl+V) ou por **e-mail**: a conta da TI (Microsoft 365) vira chamado, e a resposta por e-mail entra na conversa.
- **SLA em horas úteis**: expediente, sábado e feriados contam; o prazo pausa enquanto o chamado está "Aguardando Usuário"; há alertas de risco e violação.
- Distribuição automática por carga de trabalho, com rodízio entre os técnicos.
- Notas internas, avaliação do atendimento e fechamento automático dos resolvidos.

**Patrimônio:**
- Inventário por tipo (computadores, impressoras, celulares, rede/rack, periféricos), com histórico de responsáveis e custos.
- Manutenções e upgrades: um upgrade de componente (ex.: memória) atualiza o cadastro do equipamento.
- Estoque de periféricos com entradas e saídas.
- **Compras de TI** lidas das notas de compra do ERP (Purchase Invoice), com cadastro do equipamento a partir da nota.

**Gestão:**
- **Indicadores**: SLA, tempo de resolução, 1ª resposta, satisfação, resolução no 1º contato, reabertos, idade da fila e problemas recorrentes.
- **Visão do gestor**: valor do parque, idade, plano de renovação, gastos por ano, orçado × realizado e custo por colaborador.
- **Modo TV** em `/ti/tv?chave=…`: painel sem login para a TV da sala, com chave revogável e sem nomes de colaboradores por padrão (LGPD).

Inclui um manual em `/ti/ajuda`.

---

## Fiscal: notas e boletos

Emissão de notas e boletos em que a auxiliar de financeiro **só confere e emite**: o sistema explica, em português simples, o que vai sair e o que falta.

**Hoje funciona em modo Simulação:** o processo é completo, mas sem valor fiscal, e nada é enviado à SEFAZ, à prefeitura, ao banco ou ao cliente. Para produção, falta contratar o provedor e o banco ([veja abaixo](#o-que-falta-para-produção)).

**Notas:**
- **NFS-e** para serviços e **NF-e** para produtos, a partir da fatura de venda (Sales Invoice). Uma fatura mista gera as duas notas.
- **Conferência antes de emitir**: dados da empresa, CNPJ/CPF (inclusive o CNPJ alfanumérico de 2026), endereço, código IBGE, inscrição estadual e NCM, cada um com "como resolver".
- **Completar cadastro** sem sair da tela: o CEP preenche o endereço e o código IBGE (ViaCEP), e o CNPJ busca os dados na Receita (BrasilAPI).
- **Impostos e retenções**:
  - ISS;
  - ICMS dentro e fora do estado;
  - retenção de ISS, PIS, COFINS, CSLL e IR pelo cliente;
  - destaque informativo de CBS/IBS (reforma tributária de 2026).
- **Remessa e retorno**:
  - devolver ao cliente o equipamento que veio para calibrar ou consertar, com a chave da nota de origem validada (CFOP 5916/6916);
  - enviar equipamento nosso para fora (5915/6915), acompanhando o que está fora da empresa e avisando atrasos;
  - também demonstração e comodato.
- **Rejeições** com o motivo e o que fazer, e **Tentar de novo** sem perder o histórico.
- **Cancelamento** com as regras na tela: motivo de no mínimo 15 caracteres e prazo de 24 h da NF-e. O boleto em aberto é cancelado junto.
- DANFE e DANFSe em PDF, XML no layout da NF-e 4.00 e da NFS-e Nacional, e envio por e-mail ao cliente.

**Boletos:**
- Boleto híbrido com **Pix** (linha digitável, código de barras e Pix copia-e-cola).
- **Parcelado**: um boleto por parcela das Condições de Pagamento da fatura (ex.: 3x 30/60/90). A retenção é dividida entre as parcelas, e cada pagamento dá baixa só na sua parcela.
- Valor líquido quando o cliente retém impostos.
- **Baixa automática no ERP** quando pago: o recebimento (Payment Entry) é lançado e a retenção vai para a conta de impostos retidos. Pagamento a menor deixa a diferença em aberto; pagamento a maior vira crédito do cliente.
- Segunda via com novo vencimento, baixa manual, valor atualizado com multa e juros, lembrete antes do vencimento e cobrança depois.

**Automação e gestão:**
- Emissão em lote ("Emitir as N prontas").
- Opcional: emitir sozinho ao confirmar a fatura.
- Painel com o que falta emitir, o emitido no mês, os boletos a receber, os vencidos e o recebido.
- Página **Ir para produção** com o checklist do que falta, e manual em `/fiscal/ajuda`.

### O que falta para produção

1. **O contador valida** o código de serviço, a alíquota de ISS, os CFOPs e CSOSN/CST e as regras de retenção. Tudo é editável na Configuração Fiscal e nas Naturezas de Operação, sem mexer no código.
2. A empresa providencia o certificado digital A1, um provedor de notas (ex.: Focus NFe, PlugNotas, Nuvem Fiscal, NFE.io) e cobrança registrada com Pix no banco.
3. A TI liga o adaptador do provedor em `solucoes/fiscal/provedores.py`. As telas não mudam.
4. Testes em Homologação, depois Produção.

---

## Instalação e atualização

```bash
# primeira vez
bench get-app URL-DESTE-REPOSITORIO --branch version-16
bench --site SEU-SITE install-app solucoes

# instalação e cada atualização (depois do git pull em apps/solucoes)
bench --site SEU-SITE execute solucoes.setup.instalar
```

`solucoes.setup.instalar` sincroniza os DocTypes e grava as configurações padrão dos três módulos. Pode rodar quantas vezes quiser. Antes da primeira instalação na produção, `bench --site SEU-SITE execute solucoes.setup.conferir` faz uma checagem só de leitura.

Se o `execute` mostrar só `NameError: name 'solucoes' is not defined`, o erro real ficou escondido. Rode pelo console para ver a mensagem verdadeira:

```bash
echo 'import solucoes.setup as s; s.instalar()' | bench --site SEU-SITE console
```

## Demonstrações (nunca em produção)

| Módulo | Criar | Apagar |
|---|---|---|
| Portal | `solucoes.metrologia.simulacao.rodar` | `solucoes.metrologia.simulacao.apagar` |
| Central de TI | `solucoes.central_ti.demo.criar` e `solucoes.central_ti.demo_inventario.criar` | — |
| Fiscal | `solucoes.fiscal.demo.criar` (só em Simulação); `solucoes.fiscal.demo.parcelado` cria duas faturas parceladas a cada execução | `solucoes.fiscal.demo.apagar` |

Todas rodam com `bench --site SEU-SITE execute <comando>`. As demos criam usuários com a senha `Demo@12345`. No Fiscal, a usuária é `bia.financeiro@demo.com`.

## Estrutura

```
solucoes/
  metrologia/  portal/  api/      Portal do Cliente (DocTypes, adapters, APIs)
  central_ti/                     Central de TI (DocTypes, SLA, e-mail, APIs)
  fiscal/                         Fiscal (regras, emissão, provedores, documentos, API)
  www/                            páginas cliente, consulta, acesso, ti e fiscal
  public/portal|central|fiscal    frontends compilados (vão no git)
frontend/  frontend_ti/  frontend_fiscal/   código Vue 3 + Vite + Tailwind de cada página
dev/                              geradores dos DocTypes (python3 dev/<modulo>/gerar_doctypes.py)
```

Para alterar uma tela: `yarn install` e depois `yarn build` dentro da pasta `frontend*`. Commite o resultado em `solucoes/public/` e `solucoes/www/`.

## Compatibilidade

Frappe/ERPNext 15 (Python 3.10+) e 16. Nenhum campo é adicionado aos DocTypes nativos do ERPNext: as configurações por cliente ficam em DocTypes próprios do app.

## Licença

MIT
