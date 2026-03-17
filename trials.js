// Trials & Errors





// Open up a new window

var childWindow = null;
const waitReady = () => new Promise((resolve) => {
    childWindow.addEventListener('load', resolve, true);
});
