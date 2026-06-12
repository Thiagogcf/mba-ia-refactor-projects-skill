const sqlite3 = require('sqlite3').verbose();
const { promisify } = require('util');
const crypto = require('crypto');

const db = new sqlite3.Database(':memory:');

function dbRun(sql, params = []) {
  return new Promise((resolve, reject) =>
    db.run(sql, params, function (err) {
      err ? reject(err) : resolve({ lastID: this.lastID, changes: this.changes });
    })
  );
}

const dbGet = promisify(db.get.bind(db));
const dbAll = promisify(db.all.bind(db));

function hashPassword(pwd) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(pwd, salt, 64).toString('hex');
  return `${salt}:${hash}`;
}

async function initDb() {
  await dbRun('PRAGMA foreign_keys = ON');

  await dbRun(`CREATE TABLE users (
    id    INTEGER PRIMARY KEY,
    name  TEXT    NOT NULL,
    email TEXT    NOT NULL UNIQUE,
    pass  TEXT    NOT NULL
  )`);

  await dbRun(`CREATE TABLE courses (
    id     INTEGER PRIMARY KEY,
    title  TEXT    NOT NULL,
    price  REAL    NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
  )`);

  await dbRun(`CREATE TABLE enrollments (
    id        INTEGER PRIMARY KEY,
    user_id   INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    FOREIGN KEY (user_id)   REFERENCES users(id)   ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id)
  )`);

  await dbRun(`CREATE TABLE payments (
    id            INTEGER PRIMARY KEY,
    enrollment_id INTEGER NOT NULL,
    amount        REAL    NOT NULL,
    status        TEXT    NOT NULL,
    FOREIGN KEY (enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE
  )`);

  await dbRun(`CREATE TABLE audit_logs (
    id         INTEGER PRIMARY KEY,
    action     TEXT     NOT NULL,
    created_at DATETIME NOT NULL
  )`);

  // Seeds
  await dbRun('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
    ['Leonan', 'leonan@fullcycle.com.br', hashPassword('123')]);
  await dbRun('INSERT INTO courses (title, price, active) VALUES (?, ?, ?)',
    ['Clean Architecture', 997.00, 1]);
  await dbRun('INSERT INTO courses (title, price, active) VALUES (?, ?, ?)',
    ['Docker', 497.00, 1]);
  await dbRun('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [1, 1]);
  await dbRun('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
    [1, 997.00, 'PAID']);
}

module.exports = { db, dbRun, dbGet, dbAll, hashPassword, initDb };
