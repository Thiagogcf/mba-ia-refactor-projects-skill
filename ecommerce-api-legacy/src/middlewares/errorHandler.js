function errorHandler(err, req, res, next) {
  const status = err.statusCode || 500;
  if (status >= 500) console.error('[ERROR]', err.message, err.stack);
  res.status(status).json({ error: status >= 500 ? 'Erro interno do servidor' : err.message });
}

module.exports = errorHandler;
