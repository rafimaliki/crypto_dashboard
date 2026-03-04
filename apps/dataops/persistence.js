import { Kafka } from "kafkajs"
import { Client } from "pg"

const candle = {
	time: null,
	low: 0,
	high: 0,
	open: 0,
	current: 0,
	volume: 0
}

const client = new Client({
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD,
  host: process.env.POSTGRES_HOST,
  port: process.env.POSTGRES_PORT,
  database: process.env.POSTGRES_DB,
})

const consumer = new Kafka({
  clientId: "persistence",
  brokers: process.env.KAFKA_HOST.split(","),
}).consumer({ groupId: "persistence" })

async function write({time, low, high, open, close, volume}){
	const query = "INSERT INTO btc_usd(time, low, high, open, close, volume) VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (time) DO NOTHING;"
	await client.query(query, [time.toISOString(), low, high, open, close, volume])
	
	await updatePredictionLogs()
}

async function updatePredictionLogs() {
	try {
		const mlPredictUrl = process.env.ML_PREDICT_URL || "http://ml-predict:8000"
		const response = await fetch(`${mlPredictUrl}/update-prediction-logs`, {
			method: "POST",
			headers: { "Content-Type": "application/json" }
		})
		
		if (response.ok) {
			const result = await response.json()
			console.log(`Updated ${result.updated_count} prediction logs`)
		} else {
			console.warn(`Failed to update prediction logs: ${response.status}`)
		}
	} catch (error) {
		console.error(`Error calling prediction log update: ${error.message}`)
	}
}

await client.connect()
await consumer.connect()
await consumer.subscribe({ topic: "btc_usd", fromBeginning: true })

await consumer.run({
	eachMessage: async ({ message }) => {
		const data = JSON.parse(message.value)
		if(data.type !== "match") return
		const price = parseFloat(data.price)
		const time = new Date(data.time)
		const size = parseFloat(data.size)
		// console.log(`Processing: ${time.toISOString()}`)

		// minute granularity
		const minutes = Math.floor(time.getMinutes() / 5) * 5
		time.setMinutes(minutes)
		time.setSeconds(0);
		time.setMilliseconds(0);

		// second granularity
		// const seconds = Math.floor(time.getSeconds() / 10) * 10
        
        // time.setSeconds(seconds)
        // time.setMilliseconds(0)

		if(candle.time !== null && candle.time.getTime() === time.getTime()){
			if(price > candle.high) candle.high = price
			if(price < candle.low) candle.low = price
			candle.current = price
			candle.volume += size
		} else {
			const copy = {...candle}
			if (copy.current === 0) copy.current = price;

			candle.time = time;
			candle.current = price;
			candle.open = price;
			candle.low = price;
			candle.high = price;
			candle.volume = size;

			if(copy.time !== null){
				await write({...copy, close: copy.current, volume: copy.volume})
				console.log("Written: ", copy)
			}
		}
	}
})

