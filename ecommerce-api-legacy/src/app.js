const express = require('express');
const config = require('./config');
const { initDb } = require('./database');
const routes = require('./routes');
const errorHandler = require('./middlewares/errorHandler');

const app = express();
app.use(express.json());

initDb()
  .then(() => {
    app.use(routes);
    app.use(errorHandler);
    app.listen(config.port, () => {
      console.log(`Servidor rodando na porta ${config.port}`);
    });
  })
  .catch((err) => {
    console.error('[ERROR] Falha na inicialização:', err);
    process.exit(1);
  });
