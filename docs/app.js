document.addEventListener('DOMContentLoaded', function () {
const audioFileInput = document.getElementById('audioFileInput');
const importButton = document.getElementById('importButton');
const importFileInput = document.getElementById('importFileInput');
const exportButton = document.getElementById('exportButton');
const playPauseButton = document.createElement('button');
playPauseButton.innerText = 'Play/Pause';
document.body.insertBefore(playPauseButton, document.getElementById('waveform'));
const regionsContainer = document.getElementById('regionsContainer');

const modal = document.getElementById("modal");
const closeButton = document.querySelector(".close-button");
const saveRegionButton = document.getElementById("saveRegionButton");
const wordInput = document.getElementById('wordInput');
let currentRegion = null;
let isDragging = false;

const colors = [
    'hsla(400, 100%, 30%, 0.5)',
    'hsla(200, 50%, 70%, 0.4)',
    'hsla(100, 100%, 50%, 0.3)',
    'hsla(50, 100%, 50%, 0.3)',
    'hsla(300, 100%, 40%, 0.4)',
    'hsla(120, 60%, 70%, 0.5)',
    'hsla(0, 80%, 50%, 0.3)',
    'hsla(240, 60%, 50%, 0.3)'
];
let colorIndex = 0;

// Initialize WaveSurfer with the regions plugin
const wavesurfer = WaveSurfer.create({
    container: document.querySelector('#waveform'),
    waveColor: '#A8DBA8',
    progressColor: '#3B8686',
    backend: 'MediaElement',
    plugins: [
        WaveSurfer.regions.create({
            regionsMinLength: 0.1,
            regions: [],
            dragSelection: {
                slop: 5
            }
        })
    ]
});

// Handle play/pause button
playPauseButton.addEventListener('click', function () {
    wavesurfer.playPause();
});

// Handle file input change
audioFileInput.addEventListener('change', function (e) {
    const file = e.target.files[0];
    if (file) {
        const url = URL.createObjectURL(file);
        wavesurfer.load(url);
    }
});

// Handle import button click
importButton.addEventListener('click', function () {
    importFileInput.click();
});

// Ensure the file input reads the file and processes the JSON
importFileInput.addEventListener('change', function (e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function (event) {
            const data = JSON.parse(event.target.result);
            loadRegions(data);
        };
        reader.readAsText(file);
    }
});

// Enable drag selection after waveform is ready
wavesurfer.on('ready', function () {
    wavesurfer.enableDragSelection({
        color: colors[colorIndex % colors.length]
    });
});

// Handle region creation after drag ends
wavesurfer.on('region-created', function (region) {
    if (!region.data.imported) { // Only add if not imported
        region.color = colors[colorIndex % colors.length];
        colorIndex++;
        currentRegion = region;

        region.on('update', () => {
            isDragging = true;
        });

        region.on('update-end', () => {
            setTimeout(() => {
                if (!isDragging) {
                    openModal();
                }
                isDragging = false;
            }, 100); // Small delay to ensure dragging has ended
        });

        addRegionBlock(region); // Add region block immediately
    }
});

// Function to add region block
function addRegionBlock(region) {
    const regionBlock = document.createElement('div');
    regionBlock.className = 'region-block';
    regionBlock.style.backgroundColor = region.color;
    regionBlock.innerHTML = `
        <div class="region-header">
            <button class="toggle-button" data-id="${region.id}">▶</button>
            <span class="region-word">${region.data.word || ''}</span>
            <button data-id="${region.id}" class="delete-region-button">Delete</button>
        </div>
        <div class="region-content">
            <label>Word:</label>
            <input type="text" spellcheck="false" value="${region.data.word || ''}" data-id="${region.id}" class="region-word-input">
            <label>Start:</label>
            <input type="number" value="${region.start}" step="0.01" data-id="${region.id}" class="region-start-input">
            <label>End:</label>
            <input type="number" value="${region.end}" step="0.01" data-id="${region.id}" class="region-end-input">
        </div>
    `;
    regionsContainer.appendChild(regionBlock);

    // Add event listeners to update region on input change
    regionBlock.querySelector('.region-word-input').addEventListener('input', function (e) {
        const id = e.target.getAttribute('data-id');
        const region = wavesurfer.regions.list[id];
        region.update({ data: { word: e.target.value } });
        regionBlock.querySelector('.region-word').innerText = e.target.value; // Update word in header
    });

    regionBlock.querySelector('.region-start-input').addEventListener('input', function (e) {
        const id = e.target.getAttribute('data-id');
        const region = wavesurfer.regions.list[id];
        region.update({ start: parseFloat(e.target.value) });
    });

    regionBlock.querySelector('.region-end-input').addEventListener('input', function (e) {
        const id = e.target.getAttribute('data-id');
        const region = wavesurfer.regions.list[id];
        region.update({ end: parseFloat(e.target.value) });
    });

    // Add event listener to delete region
    regionBlock.querySelector('.delete-region-button').addEventListener('click', function (e) {
        const id = e.target.getAttribute('data-id');
        wavesurfer.regions.list[id].remove();
        regionBlock.remove();
    });

    // Add event listener to toggle region content visibility
    regionBlock.querySelector('.toggle-button').addEventListener('click', function (e) {
        const content = regionBlock.querySelector('.region-content');
        const isVisible = content.style.display === 'block';
        content.style.display = isVisible ? 'none' : 'block';
        e.target.innerHTML = isVisible ? '▶' : '▼';
    });
}

// Handle modal close button
closeButton.addEventListener('click', function () {
    closeModal();
});

// Handle modal save button and enter key
saveRegionButton.addEventListener('click', saveRegion);
wordInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        saveRegion();
    }
});

function saveRegion() {
    if (currentRegion && wordInput.value) {
        currentRegion.update({ data: { word: wordInput.value } });
        const existingBlock = regionsContainer.querySelector(`.region-block[data-id="${currentRegion.id}"]`);
        if (existingBlock) {
            existingBlock.querySelector('.region-word').innerText = wordInput.value;
            existingBlock.querySelector('.region-word-input').value = wordInput.value;
        }
        closeModal();
    }
}

// Open modal function
function openModal() {
    modal.style.display = 'block';
    wordInput.value = ''; // Clear input value
    wordInput.focus(); // Focus on input field
}

// Close modal function
function closeModal() {
    if (currentRegion) {
        currentRegion.remove();
        currentRegion = null;
    }
    modal.style.display = 'none';
}

// Load regions from JSON data
function loadRegions(data) {
    data.forEach(item => {
        const region = wavesurfer.addRegion({
            start: item.start,
            end: item.end,
            color: colors[colorIndex % colors.length],
            data: { word: item.word, imported: true }
        });
        colorIndex++;
        addRegionBlock(region); // Ensure block is added for imported regions
    });
}

// Handle export button click
exportButton.addEventListener('click', function () {
    const regions = wavesurfer.regions.list;
    const words = Object.keys(regions).map(id => ({
        start: regions[id].start,
        end: regions[id].end,
        word: regions[id].data.word
    }));
    const json = JSON.stringify(words, null, 2);
    downloadJSON(json, 'regions.json');
});

function downloadJSON(content, fileName) {
    const a = document.createElement('a');
    const file = new Blob([content], { type: 'application/json' });
    a.href = URL.createObjectURL(file);
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(a.href);
}
});
