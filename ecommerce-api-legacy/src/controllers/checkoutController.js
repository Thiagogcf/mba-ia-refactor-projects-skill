const userModel = require('../models/userModel');
const courseModel = require('../models/courseModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');
const auditModel = require('../models/auditModel');
const { PAYMENT_STATUS } = require('../models/constants');

async function checkout(req, res, next) {
  try {
    const { usr: name, eml: email, pwd: password, c_id: courseId, card } = req.body;

    if (!name || !email || !courseId || !card) {
      return res.status(400).send('Bad Request');
    }

    const course = await courseModel.findActiveById(courseId);
    if (!course) return res.status(404).send('Curso não encontrado');

    let user = await userModel.findByEmail(email);
    let userId;
    if (!user) {
      if (!password) return res.status(400).send('Bad Request');
      userId = await userModel.create(name, email, password);
    } else {
      userId = user.id;
    }

    const status = paymentModel.approveByCard(card);
    if (status === PAYMENT_STATUS.DENIED) {
      return res.status(400).send('Pagamento recusado');
    }

    const enrollment = await enrollmentModel.create(userId, course.id);
    await paymentModel.create(enrollment.lastID, course.price, status);
    await auditModel.log(`Checkout curso ${course.id} por ${userId}`);

    res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollment.lastID });
  } catch (err) {
    next(err);
  }
}

module.exports = { checkout };
