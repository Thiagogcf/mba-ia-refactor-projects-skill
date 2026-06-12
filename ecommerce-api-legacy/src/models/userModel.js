const { dbGet, dbRun, hashPassword } = require('../database');

async function findByEmail(email) {
  return dbGet('SELECT id, name, email FROM users WHERE email = ?', [email]);
}

async function create(name, email, password) {
  const result = await dbRun(
    'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
    [name, email, hashPassword(password)]
  );
  return result.lastID;
}

async function remove(id) {
  return dbRun('DELETE FROM users WHERE id = ?', [id]);
}

module.exports = { findByEmail, create, remove };
