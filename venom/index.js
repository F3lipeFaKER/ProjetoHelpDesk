const venom = require('venom-bot');
const express = require('express');
const request = require('request');

const app = express();

app.use(express.json());



let venomClient; // Variável global para armazenar o cliente do Venom

venom.create({
  session: 'helpdesk'
}).then((client) => {
  venomClient = client; // Armazena o cliente na variável global
  start();
}).catch((error) => console.log(error));

app.post('/receber_mensagem_helpdesk', (req, res) => {
  const mensagemHelpdesk = req.body.mensagem;
  const numero_cliente = req.body.numero_cliente;

  encaminharMensagemVenomBot(numero_cliente, mensagemHelpdesk)
    .then(() => {
      console.log('Mensagem enviada para o Venom Bot');
      res.sendStatus(200);
    })
    .catch((error) => {
      console.error('Erro ao enviar a mensagem para o Venom Bot:', error);
      res.sendStatus(500);
    });
});

function start() {
  venomClient.onMessage((message) => {
    if (message.isGroupMsg === false) {
      if (message.body === 'teste') {
        const numero_cliente = message.sender.id;

        const ticketData = {
          cliente: message.sender.pushname,
          telefone_cliente: numero_cliente,
          assunto: 'assunto',
          descricao: 'teste',
          status: 'Aberto',
          origem: 'Whatsapp',
          endpointHelpdesk: 'http://127.0.0.1:5000/adicionar_mensagem_helpdesk' // Endpoint configurado para receber a mensagem do helpdesk
        };

        createTicket(ticketData)
          .then((response) => {
            const ticketId = response.body.ticketId; // Verifique o campo correto que contém o ID do ticket
            console.log('Ticket criado:', ticketId);

            // Envia a resposta da requisição como uma mensagem
            venomClient.sendText(message.from, 'Ticket de atendimento criado com sucesso!\n em alguns instantes um de nossos atendentes irão entrar em contato')
              .then((result) => {
                console.log('Mensagem enviada com sucesso:', result);
              })
              .catch((error) => {

                

                console.error('Erro ao enviar a mensagem:', error);
              });
          })
          .catch((error) => {
            
            console.error('Erro ao criar o ticket:', error);
          });
      } else {
        const numero_cliente = message.sender.id;
        const mensagemData = {
          numero_cliente: numero_cliente,
          mensagem: message.body
        };
        encaminharMensagemHelpdesk(numero_cliente, mensagemData.mensagem); // Encaminha a mensagem para o endpoint de helpdesk
      }
    }
  });
}

function encaminharMensagemHelpdesk(numero_cliente, mensagem) {
  const mensagemData = {
    numero_cliente: numero_cliente,
    mensagem: mensagem
  };

  const mensagemOptions = {
    method: 'POST',
    url: 'http://127.0.0.1:5000/adicionar_mensagem_helpdesk',
    headers: {
      'Content-Type': 'application/json'
    },
    json: mensagemData // Envia o corpo da solicitação diretamente como JSON
  };

  request(mensagemOptions, (mensagemError, mensagemResponse) => {
    if (mensagemError) {
      console.error('Erro ao enviar a mensagem ao endpoint de helpdesk:', mensagemError);
    } else {
      console.log('Mensagem adicionada ao ticket:', mensagemResponse.body);

      if (mensagemResponse.body.error === 'Ticket não encontrado' && mensagemResponse.body.success === false) {
        venomClient.sendText(numero_cliente, 'Olá, Seja bem vindo, vejo que você não possui um Ticket de atendimento aberto!!\n\n Digite *teste* para proseguir com o atendimento...')
          .then((result) => {
            console.log('Mensagem de erro enviada com sucesso:', result);
          })
          .catch((error) => {
            console.error('Erro ao enviar a mensagem de erro:', error);
          });
      }
    }
  });
}

function encaminharMensagemVenomBot(numero, mensagem) {
  return venomClient.sendText(numero, mensagem);
}

function createTicket(ticketData) {
  return new Promise((resolve, reject) => {
    const options = {
      method: 'POST',
      url: 'http://127.0.0.1:5000/criar_ticket',
      headers: {},
      formData: ticketData
    };

    request(options, (error, response) => {
      if (error) {

        

        reject(error);
      } else {
        
        
        console.log('Resposta do servidor:', response.body); // Imprime a resposta completa para análise
        resolve(response);
      }
    });
  });
}

app.listen(3000, () => {
  console.log('Servidor iniciado na porta 3000');
});