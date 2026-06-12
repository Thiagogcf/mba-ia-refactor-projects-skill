const crypto = require('crypto');
const config = require('../config');

function adminAuth(req, res, next) {
  const expected = config.adminToken;
  const provided = req.headers['x-admin-token'] || '';

  let authorized = false;
  if (expected && expected.length > 0 && provided.length === expected.length) {
    try {
      authorized = crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(provided));
    } catch (_) {
      authorized = false;
    }
  }

  if (!authorized) {
    const err = new Error('Acesso negado');
    err.statusCode = 403;
    return next(err);
  }
  next();
}

module.exports = adminAuth;
