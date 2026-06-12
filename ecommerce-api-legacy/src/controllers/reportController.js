const paymentModel = require('../models/paymentModel');

async function financialReport(req, res, next) {
  try {
    const report = await paymentModel.getFinancialReport();
    res.json(report);
  } catch (err) {
    next(err);
  }
}

module.exports = { financialReport };
