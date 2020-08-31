/* vote-system */

const upvote_btns = document.querySelectorAll('.comments--comment__btn--up');
const downvote_btns = document.querySelectorAll('.comments--comment__btn--down');

if (upvote_btns && downvote_btns) {
    upvote_btns.forEach((u) => u.addEventListener('click', upvote));
    downvote_btns.forEach((d) => d.addEventListener('click', downvote));

    function makeRequest(btn, type) {
        const httpRequest = new XMLHttpRequest;

        httpRequest.onreadystatechange = function () {
            if (this.readyState == 4 && this.response == 200) {
                btn.classList.add('comments--comment__btn--active');
            } else if (this.readyState == 4 && this.response == 201) {
                btn.classList.remove('comments--comment__btn--active');
            } else if (this.readyState == 4 && this.response == 202) {
                btn.parentNode.querySelectorAll('.comments--comment__btn').forEach((btn) => btn.classList.remove('comments--comment__btn--active'));

                btn.classList.add('comments--comment__btn--active');
            }
        }

        httpRequest.open('post', '/comment/' + type + 'vote&' + btn.dataset['cm']);
        httpRequest.send();
        btn.blur();
    } 

    function upvote() {
        const btn = this;
        makeRequest(btn, 'up');
    }

    function downvote() {
        const btn = this;
        makeRequest(btn, 'down');
    }
}