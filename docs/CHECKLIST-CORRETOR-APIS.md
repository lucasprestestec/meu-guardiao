# O que o corretor precisa fazer para liberar as APIs (Azos e MAG)

Os dois pedidos podem ser feitos no mesmo dia. A Azos leva até 5 dias úteis. O prazo da MAG não está publicado.

## 1. Azos

1. Preencher o formulário de acesso: https://5lbs1.share.hsforms.com/2fsdorGblReWsU6jcieEjQg
2. A chave (API key) chega por e-mail, para o endereço do cadastro do corretor. Ela deve ser enviada ao Lucas por canal seguro, nunca em chat ou e-mail aberto.
3. Falar com o Gerente Comercial (GC) da Azos e pedir:
   - liberação das APIs de Cotação (profissões, coberturas por perfil, cálculo de prêmio) e de Coberturas;
   - ambiente de teste (sandbox), se existir;
   - limite de consultas por minuto/dia;
   - confirmação por escrito de que o preço da cotação pode ser exibido num comparador de terceiros.
4. Lembrar: a API da Azos é só de consulta. A contratação é feita no portal da Azos, e o sistema deve encaminhar o cliente para lá.

## 2. MAG

1. Criar o usuário em https://developers.mag.com.br/api-portal/user/register (dá acesso ao ambiente de teste).
2. Cadastrar o app em https://developers.mag.com.br/api-portal/myapps/new e receber as credenciais de homologação.
3. Com o acesso, baixar o Swagger da "API Seguradora" (simulação e proposta) e a seção "Autenticando sua Requisição", e enviar ao Lucas.
4. Pedir à MAG:
   - quais modelos de proposta o CNPJ do corretor pode vender (`GET /modeloproposta`);
   - credenciais de produção, quando os testes terminarem;
   - confirmação de que exibir o preço num comparador é permitido.

## 3. Confirmar com as duas (por escrito)

- Permissão contratual para exibir preço e coberturas num site comparador.
- Quem recebe a comissão quando a venda vem pelo sistema (código SUSEP e CNPJ do corretor).
- Regra de tratamento de dados pessoais (LGPD): o sistema envia idade, sexo e profissão do cliente a cada consulta.

## 4. O que o Lucas faz quando chegarem as credenciais

- Colocar as chaves só no servidor, em variáveis de ambiente: `AZOS_API_KEY`, `MAG_CLIENT_ID`, `MAG_CLIENT_SECRET`. Nunca no código nem no front.
- Ler o contrato real de cada API e implementar `cotar` em `conectores/azos.py` e `conectores/mag.py`. Sem o contrato, o formato das respostas seria chute.
- Preencher o mapeamento dos códigos de cobertura de cada seguradora para os códigos internos, com validação do corretor.
