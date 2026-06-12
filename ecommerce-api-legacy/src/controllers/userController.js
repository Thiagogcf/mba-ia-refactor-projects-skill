const userModel = require('../models/userModel');

async function remove(req, res, next) {
  try {
    await userModel.remove(req.params.id);
    res.send('Usuário deletado com sucesso');
  } catch (err) {
    next(err);
  }
}

module.exports = { remove };
