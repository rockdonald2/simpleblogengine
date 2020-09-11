const reply_btn = document.querySelectorAll('.comments--comment__btn--reply');
const rereply_btn = document.querySelectorAll('.comments--reply__btn--reply');
const cancel_btn = document.querySelectorAll('.comments--comment__reply--cancel');
const recancel_btn = document.querySelectorAll('.comments--reply__rereply--cancel');

if (reply_btn && rereply_btn && cancel_btn && recancel_btn) {
    reply_btn.forEach((r) => r.addEventListener('click', toggleReply));
    rereply_btn.forEach((r) => r.addEventListener('click', toggleReply));
    cancel_btn.forEach((c) => c.addEventListener('click', cancelReply));
    recancel_btn.forEach((c) => c.addEventListener('click', cancelReply));

    function toggleReply(event) {
        const elem = this.parentNode.parentNode.querySelector('.comments--comment__reply') || this.parentNode.parentNode.querySelector('.comments--reply__rereply');
        elem.classList.toggle('hide');
    }

    function cancelReply(event) {
        this.parentNode.parentNode.classList.add('hide');
    }
}