document.getElementById("retrieve").addEventListener("click", retrieveAction);

document.getElementById("symbol").addEventListener("keypress", function(event) {
  if (event.key === "Enter") {
    retrieveAction(event);
  }
});


window.onload = (event) => {
let symbolField = document.getElementById('submittedSymbol');
if (symbolField && symbolField.value) {
  makePlot(symbolField.value);
}    
};

//!!!!!!!!1!!function makeplot(stock_code, chart_type) 
function makePlot(stockSymbol) {
fetch('/info/pricing/'+stockSymbol)
.then(response => response.json())
.then(data => {
  // Create Plotly chart with the data
  const chartData = [{
    x: data.dates,
    y: data.adjClosePrices,
    type: 'scatter',
    mode: 'lines',
    marker: {
      color: 'blue'
    }
  }];

  const layout = {
    title: 'Stock Prices for ' + stockSymbol.toUpperCase(),
    xaxis: {
      title: 'Date'
    },
    yaxis: {
      title: 'Adjusted Close Price'
    }
  };

  Plotly.newPlot('myChart', chartData, layout);
})
.catch(error => {
  console.error('Error fetching data:', error);
});
}

function retrieveAction(event) {
  event.preventDefault(); 
  let symbol = document.getElementById('symbol').value;
  if (symbol) {
      window.location.href = '/info/' + symbol.toUpperCase();
  }
}
