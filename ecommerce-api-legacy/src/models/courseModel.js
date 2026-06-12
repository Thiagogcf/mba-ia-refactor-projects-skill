const { dbGet } = require('../database');

async function findActiveById(id) {
  return dbGet('SELECT * FROM courses WHERE id = ? AND active = 1', [id]);
}

module.exports = { findActiveById };
