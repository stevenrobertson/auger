rand_norm = (mean, std_ratio) ->
  vals = new Uint32Array(2)
  crypto.getRandomValues vals
  u = vals[0] / 0xffffffff
  v = vals[1] / 0xffffffff
  mean * (1 + std_ratio * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v))

generate_random_request = (i) ->
  startTime = Math.random() * 30
  byteTarget = Math.floor((32 + 256 * Math.random()) * 1024)
  samples = [{timeSinceStart: 0, loaded: 0, duration: 0, loadedDelta: 0}]
  sum = 0
  sumDur = 0
  while sum < byteTarget
    packet_size = 1480
    # 4Mbps line, normally distributed. TODO(strobe): get real statistics
    rate = Math.max(0, rand_norm(4000 * 1024 / 8, 0.2))
    # TODO(strobe): beta distribution
    duration = Math.floor(Math.random() * 50 + 50) / 1000
    bytes = packet_size * Math.round(rate * duration / packet_size)
    if sum + bytes >= byteTarget
      bytes = byteTarget - sum
      duration = Math.round(bytes / rate * 1000) / 1000
    sum += bytes
    sumDur += duration
    samples.push {
      timeSinceStart: sumDur,
      duration: duration,
      loaded: sum,
      loadedDelta: bytes
    }
    if samples.length > 10000
      debugger
  return {
    id: i
    startOffset: startTime
    duration: sumDur
    bytes: sum
    samples: samples
  }

generate_random_data = () ->
  requests = (generate_random_request(i) for i in [0 .. 50])
  requests.sort((a, b) -> a.startOffset - b.startOffset)
  return requests

#resample_requests = (ts, te, nsteps, requests)
  #for req in requests
    #values = for
    #
resample = (request, times) ->
  # TODO(strobe): This is an exemplar of a few kinds of methods I think would
  # be generally useful, and should probably be systematized so that they can
  # be generalized against:
  #   - Resampling methods
  #   - Sliding-window maps (for time-series or other computations, operating
  #     a map function over a dataset that may be large but will often have a
  #     limited working set within a particular time range)
  #   - Finite-difference methods (when I eventually get around to designing a
  #     soft set of type hints to apply to data so that comparisons can be
  #     auto-suggested and populated, finite-difference types need a separate
  #     composable notation so they can be appropriately reconstructed)
  sum = 0
  i = 0
  result = []
  for t in times
    dt = t - request.startOffset
    oldSum = sum

    # Find the first request whose sample position is after the current time,
    # without going past the end of the array.
    while (i < request.samples.length - 1 and request.samples[i].timeSinceStart < dt)
      i++

    s = request.samples[i]

    if s.timeSinceStart > dt
      # The end time (and possibly start time) of the sample is in the future.
      if s.duration > 0
        sample_proportion_remaining = (s.timeSinceStart - dt) / s.duration
        sum = s.loaded - s.loadedDelta * Math.min(1, sample_proportion_remaining)
      else
        # Duration is 0, avoid a divide-by-zero.
        sum = s.loaded - s.loadedDelta
    else
      # The end time is in the past (probably at the end of the array).
      sum = s.loaded

    result.push {time: t, bytes: sum, delta: sum - oldSum}
  return result

layerize_requests = (requests, nsamples, tstart, tend) ->
  tstart ?= 0
  tend ?= d3.max(requests, (r) -> r.start + r.duration)
  tskip = (tend - tstart) / (nsamples - 1)
  times = (tstart + tskip * i for i in [0..nsamples])
  requests.map((r) -> {
    id: r.rid,
    name: r.rid + ' itag=' + r.itag + ' range=' + r.range,
    values: resample(r, times).map (s) -> {x: s.time, y: s.delta / tskip}
  })

simplify_layers_in_place = (layers) ->
  for layer in layers
    values = [layer.values[0]]
    for i in [1...layer.values.length-1]
      last = layer.values[i-1].y
      cur = layer.values[i].y
      next = layer.values[i+1].y
      if last == cur and cur == next
        continue
      last = layer.values[i-1].y + layer.values[i-1].y0
      cur = layer.values[i].y + layer.values[i].y0
      next = layer.values[i+1].y + layer.values[i+1].y0
      if last == cur and cur == next
        continue
      values.push layer.values[i]
    values.push layer.values[layer.values.length-1]
    layer.values = values

main = (data) ->
    chart = d3.select("body").append("svg")
        .attr("class", "chart")
        .attr("id", "foo")

    #data = generate_random_data()

    layers = for j in [0..10]
      {layer: j,
      values: {x: i, y: Math.random() * 10} for i in [0..50]}

    max_time = d3.max data, (r) ->
      r.startOffset + r.samples[r.samples.length-1].timeSinceStart
    layers = layerize_requests(data, 5000, 0, max_time)

    stack = d3.layout.stack()
      .values((d) -> d.values)
    stacked_data = stack(layers)
    simplify_layers_in_place stacked_data

    max_val = d3.max stacked_data, (s) ->
      d3.max s.values, (v) -> v.y + v.y0
    max_val = Math.min max_val, 5000000

    x = d3.scale.linear()
      .domain([0, max_time])
      .range([0, 1500])

    y = d3.scale.linear()
      .domain([0, max_val])
      .range([800, 0])

    color = d3.scale.category10()

    area = d3.svg.area()
      .x((d) -> x(d.x))
      .y0((d) -> y(d.y0))
      .y1((d) -> y(d.y0 + d.y))

    chart.selectAll("path")
        .data(stacked_data)
      .enter().append("path")
        .attr("class", "layer")
        .attr("d", (d) -> area(d.values))
        .style("fill", (d) -> color(d.id % 10))
      .append("title")
        .text((d) -> d.name)

    xAxis = d3.svg.axis()
      .scale(x)
      .orient("bottom")
    chart.append("g")
      .attr("class", "x axis")
      .call(xAxis)

    yAxis = d3.svg.axis()
      .scale(y)
      .orient("right")
    chart.append("g")
      .attr("class", "y axis")
      .call(yAxis)

    zoom = d3.behavior.zoom().x(x).on "zoom", () ->
      chart.select(".x.axis").call(xAxis)
      chart.selectAll(".layer")
        .attr("d", (d) -> area(d.values))
    chart.call(zoom)

    #chart.selectAll("").data(data)
      #.enter().append("rect")
        #.attr("y", (d, i) -> i * 20)
        #.attr("width", x)
        #.attr("height", 20)

    #xhr = new XMLHttpRequest()
    #xhr.open "GET", "/data/test4.txt"
    #xhr.addEventListener 'loadend', (evt) ->
        #console.log(xhr.responseText)
    #xhr.send()

$(document).ready () ->
  xhr = new XMLHttpRequest()
  report = /report=([^&]*)/.exec(location.search)[1]
  xhr.open "GET", "/static/reports/#{report}.json"
  xhr.addEventListener 'loadend', (evt) -> main JSON.parse(xhr.response)
  xhr.send()
