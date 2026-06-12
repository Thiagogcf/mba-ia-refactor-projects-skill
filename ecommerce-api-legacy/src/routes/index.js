const { Router } = require('express');
const checkoutController = require('../controllers/checkoutController');
const reportController = require('../controllers/reportController');
const userController = require('../controllers/userController');
const adminAuth = require('../middlewares/adminAuth');

const router = Router();

router.post('/api/checkout', checkoutController.checkout);
router.get('/api/admin/financial-report', adminAuth, reportController.financialReport);
router.delete('/api/users/:id', adminAuth, userController.remove);

module.exports = router;
