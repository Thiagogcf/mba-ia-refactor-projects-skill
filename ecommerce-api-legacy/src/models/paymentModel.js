const { dbRun, dbAll } = require('../database');
const { PAYMENT_STATUS } = require('./constants');

function approveByCard(cardNumber) {
  return cardNumber.startsWith('4') ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
}

async function create(enrollmentId, amount, status) {
  return dbRun(
    'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
    [enrollmentId, amount, status]
  );
}

async function getFinancialReport() {
  const rows = await dbAll(`
    SELECT
      c.id    AS course_id,
      c.title,
      u.name  AS student_name,
      p.amount,
      p.status
    FROM courses c
    LEFT JOIN enrollments e ON e.course_id = c.id
    LEFT JOIN users u       ON u.id = e.user_id
    LEFT JOIN payments p    ON p.enrollment_id = e.id
    ORDER BY c.id
  `);

  const coursesMap = {};
  for (const row of rows) {
    if (!coursesMap[row.course_id]) {
      coursesMap[row.course_id] = { course: row.title, revenue: 0, students: [] };
    }
    if (row.student_name) {
      if (row.status === PAYMENT_STATUS.PAID) {
        coursesMap[row.course_id].revenue += row.amount;
      }
      coursesMap[row.course_id].students.push({
        student: row.student_name || 'Unknown',
        paid: row.amount || 0,
      });
    }
  }
  return Object.values(coursesMap);
}

module.exports = { approveByCard, create, getFinancialReport };
