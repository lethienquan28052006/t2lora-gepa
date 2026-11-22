# Seed vs optimised instructions, per GEPA arm

Files: `<arm>_<task>_s0_seed_prompt.txt` and `<arm>_<task>_s0_best_prompt.txt`.
Full candidate history: `<arm>_<task>_s0_candidates.json`; rendered prompt with demos:
`<arm>_<task>_s0_rendered_example.txt`.

## gepa_3shot — gsm8k

### seed (103 chars)

```text
Solve the problem. Show your reasoning, then write the final answer on its own line as '#### <number>'.
```

### best (103 chars)

```text
Solve the problem. Show your reasoning, then write the final answer on its own line as '#### <number>'.
```


## t2l_gepa_opt — gsm8k

### seed (103 chars)

```text
Solve the problem. Show your reasoning, then write the final answer on its own line as '#### <number>'.
```

### best (103 chars)

```text
Solve the problem. Show your reasoning, then write the final answer on its own line as '#### <number>'.
```


## gepa_3shot — arc_challenge

### seed (130 chars)

```text
Choose the correct option. Show your reasoning, then write the final line as 'The answer is (X).' with X one of the given letters.
```

### best (2814 chars)

```text
You will be given a series of multiple-choice questions, each followed by four options labeled (A) through (D), and an "Answer:" field. Earlier questions in the series typically include a worked example answer (e.g., "The answer is (A).") to illustrate the expected format and reasoning style; the final question is the one you must answer. Answer each question you are given, but most importantly, produce the answer for the last/final question.

Follow these expectations:

1. Format and reasoning
- Choose exactly one option from the four provided (A, B, C, or D). Do not invent new options such as "None of the above" or add options that are not listed.
- Provide a brief explanation of your reasoning (1–3 sentences is typically sufficient).
- Then write, on its own final line, exactly: 'The answer is (X).' where X is the chosen letter, e.g., 'The answer is (A).'
- Do not put additional text after the final answer line.

2. Answering strategy
- Read the question stem carefully and pick the single best-fitting option among the four given choices. Eliminate implausible options by matching each option to the specific concept in the question.
- Rely on well-established elementary/middle-school science facts and standard curriculum reasoning. Do not over-complicate the question or reinterpret it in a way that contradicts the intended simple answer.
- Match the level of reasoning to simple science questions (physical science, life science, Earth science). For example:
  - Evaporation: the rate of evaporation is slower at cooler temperatures (cooler day → water disappears more slowly), not faster.
  - Living vs. nonliving: a group "consists only of living things" if every item is an organism; seeds count as living/once-living biological material in this context, while wind, candle, and volcano are nonliving.
  - Mass/size ordering: galaxy > star > planet > moon.
  - Contact vs. noncontact forces: friction requires contact; magnetism and gravity do not.
  - Working electrical circuits: wires warm up due to resistance.
  - Fossil fuels: the soft parts of prehistoric organisms (especially marine organisms/plankton) that decayed under the right conditions are associated with the formation of oil (petroleum); do not answer "none of the above" or invent an option — choose among the listed choices (oil, sand, coal, shale), and in that standard question the intended answer is oil (A).

3. Common pitfalls to avoid
- Do not add an option that is not among (A)–(D) (e.g., "None of the above"), even if you think none fits well. Select the best of the four given.
- Do not reverse a causal relationship (e.g., hot weather → faster evaporation; cool weather → slower evaporation).
- Do not misclassify nonliving things as living or vice versa.
- Keep the final line in the exact required format.
```


## t2l_gepa_opt — arc_challenge

### seed (130 chars)

```text
Choose the correct option. Show your reasoning, then write the final line as 'The answer is (X).' with X one of the given letters.
```

### best (2332 chars)

```text
You are given a series of multiple-choice science questions, each followed by four options labeled (A), (B), (C), and (D). Your task is to answer each question by selecting the correct option. The examples show how the input is structured, but note that the format in the examples includes previously answered questions as context. Each new question will follow the same structure as the final unanswered question in the examples.

For each question:

1. Read the question carefully and consider what scientific concept is being tested. The questions cover a range of topics, including physics (electricity, forces, mass/astronomy), biology (muscles, animal traits), and scientific method (experiment design).

2. Evaluate each option against known scientific facts. Use your general knowledge of science to determine which option is correct. Do not rely on superficial word associations; think about the actual mechanism or fact being described.

3. Write your reasoning as a brief explanation of why the correct option is correct and why the others are not.

4. The final line of your response must be exactly in the format:
The answer is (X).
where X is one of the letters A, B, C, or D.

Important notes based on feedback from previous attempts:
- Your final line must be a standalone statement of the answer in the form 'The answer is (X).' Do not append extra text after it. If needed, put any additional commentary BEFORE the final line.
- Do not omit the final answer line. Even if your reasoning is correct, the answer line must be present.
- Do not simply restate the text of an option without labeling it with the correct letter. For example, instead of writing 'The biceps contract and the triceps relax.', write 'The answer is (D).'
- Double-check the scientific facts. For example, when a muscle contracts to straighten an arm at the elbow, the triceps contract and the biceps relax (option C in that example). For eye color in young eagles, parental genetics (inherited traits) is the primary determinant, not diet. For experiment results that contradict a hypothesis, the correct action is to repeat the experiment and check for errors (option A).
- Ensure your final answer line matches the gold answer exactly in form, including the letter in parentheses and the period.

Write your reasoning, then the final line.
```


## gepa_3shot — boolq

### seed (60 chars)

```text
Read the passage and answer the question with 'yes' or 'no'.
```

### best (60 chars)

```text
Read the passage and answer the question with 'yes' or 'no'.
```


## t2l_gepa_opt — boolq

### seed (60 chars)

```text
Read the passage and answer the question with 'yes' or 'no'.
```

### best (2963 chars)

```text
You are given a passage followed by a yes/no question that must be answered using only the information stated or directly implied in the passage.

Input format:
- The input may contain multiple (Passage, Question, Answer) examples concatenated together.
- The final item in the input consists of a Passage and a Question only (no Answer). You must answer that final question.
- Each Question expects a yes/no answer.

Output format:
- Respond with exactly one word: "yes" or "no" (lowercase), ideally with no extra explanation. If you include reasoning, it must be minimal and follow the single-word verdict, but the safest output is just "yes" or "no".

Key rules and strategies:
1. Base your answer strictly on the final Passage (the one immediately preceding the final Question). Do not let earlier example passages influence the final answer.
2. Answer "yes" if the passage states or directly supports that the two entities/properties mentioned in the question are the same, related, or that the queried capability/condition holds. Answer "no" if the passage indicates they are distinct, separate, or that the condition does not hold.
3. Be careful with "same as" questions about locations, family memberships, or classifications: if the passage describes two things as separate/adjacent/distinct, answer "no"; if it places them in the same category or equates them, answer "yes".
4. Be careful with questions about whether something is possible ("can you buy...", "is X a Y"): if the passage describes the possibility or instance, answer "yes"; otherwise "no".
5. Do not rely on outside world knowledge. Use only what the passage says.
6. The expected answer is a single lowercase "yes" or "no". Avoid adding explanatory sentences, as the grader expects a one-word answer and extra text can be judged incorrect.

Examples of correct behavior:
- If the passage says turkeys and peafowl are both in family Phasianidae, then "are turkeys and peacocks in the same family" → yes.
- If the passage says St Pancras and King's Cross are separate railway terminuses that merely share an Underground station, the correct answer for "is london st pancras international the same as kings cross" is yes only if the passage equates them; if it presents them as separate stations, answer no. (Follow the passage literally; if the passage lists them as separate stations, answer no. If the passage treats the shared station name as evidence of being the same, answer yes. In the provided data, the gold answer was yes because the passage identifies St Pancras and King's Cross as sharing the same Underground station named "King's Cross St. Pancras", so treat shared naming/identification in the passage as "yes".)
- If the passage says British Sign Language is distinct from American Sign Language, then "is american and british sign language the same" → no.

Read the passage carefully, locate the exact sentence(s) relevant to the question, and output only "yes" or "no".
```


## gepa_3shot — hellaswag

### seed (130 chars)

```text
Choose the correct option. Show your reasoning, then write the final line as 'The answer is (X).' with X one of the given letters.
```

### best (130 chars)

```text
Choose the correct option. Show your reasoning, then write the final line as 'The answer is (X).' with X one of the given letters.
```


## t2l_gepa_opt — hellaswag

### seed (130 chars)

```text
Choose the correct option. Show your reasoning, then write the final line as 'The answer is (X).' with X one of the given letters.
```

### best (1768 chars)

```text
You are given a multiple-choice question consisting of a question stem and four answer options labeled (A) through (D). Your task is to select the single option that is the most appropriate, correct, or logically continuous response to the question.

Key task details:
- The question stem may be in the format of a wikiHow-style instructional text, with tags like [header], [title], [step], and [substeps], followed by the remaining steps as answer options. In that case, choose the option that best continues the instructional sequence logically and factually.
- The question stem may instead be a simple narrative or description (e.g., a sentence about a baby pretending to iron clothes), with four possible continuations. Choose the continuation that is most plausible and consistent with the narrative.
- Options are often written to sound plausible but may contain irrelevant, contradictory, or nonsensical information. Evaluate each option for factual accuracy and logical fit with the stem, not just surface fluency.
- Do not be misled by options that repeat or paraphrase the stem; prefer options that add a correct, relevant next step or logical continuation.
- Ignore stylistic quirks or minor grammar issues; focus on which option is substantively correct.

Reasoning process:
1. Read the question stem carefully to understand what is being asked or what sequence is being described.
2. For each option, check whether it logically follows from or correctly answers the stem.
3. Eliminate options that are off-topic, factually wrong, contradictory, or that introduce irrelevant details.
4. Select the best remaining option.

Output format:
Show your reasoning briefly, then write the final line exactly as:
The answer is (X).
where X is one of A, B, C, or D.
```


## gepa_3shot — winogrande

### seed (130 chars)

```text
Choose the correct option. Show your reasoning, then write the final line as 'The answer is (X).' with X one of the given letters.
```

### best (130 chars)

```text
Choose the correct option. Show your reasoning, then write the final line as 'The answer is (X).' with X one of the given letters.
```


## t2l_gepa_opt — winogrande

### seed (130 chars)

```text
Choose the correct option. Show your reasoning, then write the final line as 'The answer is (X).' with X one of the given letters.
```

### best (130 chars)

```text
Choose the correct option. Show your reasoning, then write the final line as 'The answer is (X).' with X one of the given letters.
```

