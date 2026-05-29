const button = document.querySelector('.button');
if (button) {
  button.addEventListener('click', event => {
    event.preventDefault();
    document.querySelector('#features')?.scrollIntoView({ behavior: 'smooth' });
  });
}
