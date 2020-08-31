/* deleting comments */

const del_button = document.querySelectorAll('.comments #del_button') || null;

if (del_button) {
    del_button.forEach((d) => d.addEventListener('click', del));

    function del(event) {
        const httpRequest = new XMLHttpRequest;
        const btn = this;

        httpRequest.onreadystatechange = function () {
            if (this.readyState == 4 && this.response == 201) {
                btn.parentNode.innerHTML = 'This comment was deleted';
            }
        }

        httpRequest.open('POST', '/comment/delete&' + this.dataset['cm']);
        httpRequest.send();
        this.blur();
    }
}