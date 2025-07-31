// server.js
const express = require('express');
const si = require('systeminformation');
const cors = require('cors');

const app = express();
const port = 3000;

app.use(cors()); // Maakt CORS-communicatie mogelijk voor externe clients

// Endpoint voor CPU-informatie
app.get('/api/cpu', async (req, res) => {
  try {
    const cpuData = await si.currentLoad();
    res.json({ load: cpuData.currentLoad, cores: cpuData.cpus });
  } catch (error) {
    res.status(500).send('Error retrieving CPU data');
  }
});

// Endpoint voor geheugeninformatie
app.get('/api/memory', async (req, res) => {
  try {
    const memoryData = await si.mem();
    res.json({
      used: (memoryData.active / (1024 ** 3)).toFixed(2),  // In GB
      total: (memoryData.total / (1024 ** 3)).toFixed(2),   // In GB
      free: (memoryData.available / (1024 ** 3)).toFixed(2) // In GB
    });
  } catch (error) {
    res.status(500).send('Error retrieving memory data');
  }
});

// Endpoint voor netwerkverkeer
app.get('/api/network', async (req, res) => {
  try {
    const networkData = await si.networkStats();
    res.json({
      rx: (networkData[0].rx_bytes / (1024 ** 2)).toFixed(2), // Ontvangen in MB
      tx: (networkData[0].tx_bytes / (1024 ** 2)).toFixed(2)  // Verzonden in MB
    });
  } catch (error) {
    res.status(500).send('Error retrieving network data');
  }
});

// Endpoint voor schijfinformatie
app.get('/api/disk', async (req, res) => {
  try {
    const diskData = await si.fsSize();
    res.json(diskData.map(disk => ({
      filesystem: disk.fs,
      used: (disk.used / (1024 ** 3)).toFixed(2), // Gebruikt in GB
      size: (disk.size / (1024 ** 3)).toFixed(2)  // Totaal in GB
    })));
  } catch (error) {
    res.status(500).send('Error retrieving disk data');
  }
});

// Endpoint voor systeemtemperatuur (als ondersteund door hardware)
app.get('/api/temperature', async (req, res) => {
  try {
    const tempData = await si.cpuTemperature();
    res.json({ main: tempData.main, cores: tempData.cores });
  } catch (error) {
    res.status(500).send('Error retrieving temperature data');
  }
});

app.listen(port, () => {
  console.log(`Server monitoring API running at http://localhost:${port}`);
});


async function fetchStats() {
    try {
        // Fetch data from the server
        const [cpuRes, memRes, diskRes, networkRes] = await Promise.all([
            fetch('http://localhost:3000/api/cpu'),
            fetch('http://localhost:3000/api/memory'),
            fetch('http://localhost:3000/api/disk'),
            fetch('http://localhost:3000/api/network')
        ]);

        const cpuData = await cpuRes.json();
        const memData = await memRes.json();
        const diskData = await diskRes.json();
        const networkData = await networkRes.json();

        // Update CPU stats
        document.querySelector('#cpu-usage').textContent = `${cpuData.load.toFixed(2)}%`;
        document.querySelector('#cpu-progress').style.width = `${cpuData.load.toFixed(0)}%`;

        // Update RAM stats
        document.querySelector('#ram-usage').textContent = `${((memData.used / memData.total) * 100).toFixed(2)}%`;
        document.querySelector('#ram-progress').style.width = `${((memData.used / memData.total) * 100).toFixed(0)}%`;

        // Update Disk stats (showing the first disk as an example)
        if (diskData.length > 0) {
            const diskUsed = ((diskData[0].used / diskData[0].size) * 100).toFixed(2);
            document.querySelector('#disk-usage').textContent = `${diskData[0].used} GB`;
            document.querySelector('#disk-progress').style.width = `${diskUsed}%`;
        }

        // Update Network stats (e.g., received bytes)
        document.querySelector('#network-usage').textContent = `${networkData.rx} MB`;
        document.querySelector('#network-progress').style.width = `50%`; // Example, adjust based on more specific usage needs

    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

// Fetch data every 5 seconds
setInterval(fetchStats, 5000);
fetchStats();