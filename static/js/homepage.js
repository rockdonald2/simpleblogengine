/* 
 * Empty container to fetch posts in
 */
const posts = [];
// * Important variables for pagination
let page = 1;
const limit = 5;
const currentlyShownPostNodes = [];
let currentTotalPageNumber = 0;
const secretLimit = 2;

/* We make the HTTP requests to get the posts */
const httpRequest = new XMLHttpRequest;

httpRequest.onreadystatechange = function () {
    if (this.readyState == 4 && this.status == 200) {
        posts.push(...JSON.parse(this.response));
        makePaginationBar(Math.ceil(posts.length / limit));
        populateList(posts);
    } else if (this.readyState == 4) {
        window.location.replace(this.responseURL);
    }
}

httpRequest.open('get', '/posts');
httpRequest.send();

/* A few essential container nodes, and search input node */
const postsContainer = document.querySelector('.posts--container');
const searchInput = document.querySelector('.posts--form input[type="text"]');
const paginationBar = document.querySelector('.posts--pagination');

/* This function find the matches in the titles, and filters the posts accordingly,
returns the filtered copy of the posts */
function findMatches(wordToMatch) {
    return posts.filter(post => {
        const regex = new RegExp(wordToMatch, 'gi');
        return post['title'].match(regex);
    });
}

/* 
Invokes the populateList, find the correct posts array
*/
function displayMatches() {
    const matchPosts = findMatches(this.value);
    populateList(matchPosts, this.value);
}

searchInput.addEventListener('change', displayMatches);
searchInput.addEventListener('keyup', displayMatches);

/* 
This function populates the DOM with the filtered/unfiltered posts
*/
function populateList(posts, keywords = '') {
    postsContainer.innerHTML = '';

    if (!posts.length) {
        /* if the posts array is empty */
        postsContainer.innerHTML = '<p class="posts--empty">There are no posts...</p>';
        paginationBar.classList.add('hide');
        return;
    }

    paginationBar.classList.remove('hide');

    let pageCounter = 1;
    let postCounter = 1;

    /* if there are posts */
    for (let p of posts) {
        const regex = new RegExp(keywords, 'gi');
        const title = p['title'].replace(regex, `<span class="posts--post__top--title__hl">${keywords}</span>`);

        postsContainer.innerHTML += `
        <a href="post/${p['_id']}"
            class="posts--post hide"
            data-page="${pageCounter}">
            <div class="posts--post__top">
                <span class="posts--post__top--title">${title}</span><span>Read more<span><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
</svg></span>
            </div>
            <div class="posts--post__bottom">
                <span>${p['author']} | ${p['date']}</span>
            </div>
        </a>`;

        if (!(postCounter % limit)) {
            pageCounter++;
        }
        postCounter++;
    }

    currentTotalPageNumber = pageCounter - 1;

    /* we only need the bar if there are any posts */
    updatePaginationBar(pageCounter);
    showPage(event = null, pageNumber = 1);
}

/* 
This function takes care of the pagination, only shows the posts which belong to the relevant page.
All posts are always in the DOM.
*/
function showPage(event = null, pageNumber = null) {
    const pageDivider = pageNumber || this.dataset['page'];
    const relevantPostsNodes = document.querySelectorAll(`.posts--post[data-page="${pageDivider}"]`);

    for (const p of currentlyShownPostNodes.slice()) {
        p.classList.add('hide');
        currentlyShownPostNodes.shift();
    }

    for (const p of relevantPostsNodes) {
        p.classList.remove('hide');
        currentlyShownPostNodes.push(p);
    }

    document.querySelector('.posts--pagination button.active').classList.remove('active');
    const currPage = document.querySelector(`.posts--pagination button[data-page="${pageDivider}"]`);
    currPage.classList.add('active');
    currPage.blur();
    if (currentTotalPageNumber >= 10) secretPagination();
}

/* 
Remades the paginationBar with the page numbers each time the DOM is updated by the populateList function
*/
function makePaginationBar(pageNumber) {
    for (let i = 1; i <= pageNumber; i++) {
        const node = document.createElement('button');
        node.type = 'button';
        node.addEventListener('click', showPage);
        node.dataset['page'] = i;
        node.innerHTML = i;

        if (i == 1) {
            node.classList.add('active');
        }

        paginationBar.appendChild(node);
    }
}

/* 
Updates the pagination bar, according to the current counter.
Hides unnecessary pagination bar buttons.
*/
function updatePaginationBar() {
    const paginationNodes = Array.from(document.querySelectorAll('.posts--pagination button'));
    const unnecessaryNodes = paginationNodes.filter((n) => n.dataset['page'] > currentTotalPageNumber);

    paginationNodes.forEach((n) => n.classList.remove('hide'));
    unnecessaryNodes.forEach((n) => n.classList.add('hide'));

    /* If there are too many pages, hide the central ones,
    We hide pages that are 3 pages apart from the active one,
    But, we always show the first, and the last number.
    */
    if (currentTotalPageNumber >= 10) secretPagination();
}

function secretPagination() {
    const paginationNodes = Array.from(document.querySelectorAll('.posts--pagination button')).filter((n) => n.dataset['page'] <= currentTotalPageNumber);
    paginationNodes.forEach((n) => n.classList.remove('hide'));
    const currentActivePage = parseInt(document.querySelector('.posts--pagination button.active').dataset['page']);
    const secretPages = paginationNodes.filter((n) =>
        Math.abs(n.dataset['page'] - currentActivePage) > secretLimit &&
        n.dataset['page'] != 1 &&
        n.dataset['page'] != currentTotalPageNumber);
    secretPages.forEach((n) => n.classList.add('hide'));
}