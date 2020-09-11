/* deleting comments */

const del_button = document.querySelectorAll('.comments--comment__btn--delete');
const del_reply_button = document.querySelectorAll('.comments--reply__btn--delete')

if (del_button && del_reply_button) {
    del_button.forEach((d) => d.addEventListener('click', del));
    del_reply_button.forEach((d) => d.addEventListener('click', del));

    function del(event) {
        const httpRequest = new XMLHttpRequest;
        const btn = this;

        httpRequest.onreadystatechange = function () {
            if (this.readyState == 4 && this.response == 200) {
                btn.parentNode.innerHTML = '<p class="comments--comment__text">This comment was deleted</p>';
            } else if (this.readyState == 4) {
                window.location.replace(this.responseURL);
            }
        }

        httpRequest.open('POST', '/comment/delete&' + this.dataset['cm']);
        httpRequest.send();
        this.blur();
    }
}