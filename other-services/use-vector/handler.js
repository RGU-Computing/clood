'use strict';

const use = require("@tensorflow-models/universal-sentence-encoder");
const similarity = require("compute-cosine-similarity");

/**
 * Asynchronus function to generate the vector representation of a piece of text.
 * @param {string} text 
 */
async function encodeData (text) {
  // const sentences = [text];
  let model = await use.load();
  let embeddings = await model.embed(text); // `embeddings` is a 2D tensor consisting of the 512-dimensional embeddings for each sentence.
  let d = await embeddings.array();
  return d[0]; // extract and return vector
}

/**
 * Test endpoint.
 */
module.exports.home = async event => {
  return {
    statusCode: 200,
    body: JSON.stringify(
      {
        message: 'Serverless v1.0! You can convert texts to vectors!',
        input: event
      },
      null,
      2
    )
  };
};

/**
 * Vectorise text in request path.
 */
module.exports.vectoriseInPath = async event => {
  const text = [event.pathParameters.text];
  const vec = await encodeData(text);
  return {
    statusCode: 200,
    body: JSON.stringify({
      message: 'Vector representation using lite Universal Sentence Encoder',
      inputText: text[0],
      vectors: vec
    })
  };
};

/**
 * Vectorise text in request body.
 */
module.exports.vectorise = async event => {
  const data = JSON.parse(event.body);
  const text = [data.text];
  const vec = await encodeData(text);
  return {
    statusCode: 200,
    body: JSON.stringify({
      message: 'Vector representation using lite Universal Sentence Encoder',
      inputText: text[0],
      vectors: vec
    })
  };
};

/**
 * Determine cosine similarity of two pieces of texts in request body.
 */
module.exports.similarity = async event => {
  // const data = querystring.parse(event.body);
  const data = JSON.parse(event.body);
  const first = [data.first];
  const second = [data.second];
  const firstVec = await encodeData(first);
  const secondVec = await encodeData(second);
  const sim = similarity(firstVec, secondVec);
  return {
    statusCode: 200,
    body: JSON.stringify({
      message: 'Cosine similarity between vectorised input texts',
      inputTexts: [first[0], second[0]],
      similarity: sim
    })
  };
};
