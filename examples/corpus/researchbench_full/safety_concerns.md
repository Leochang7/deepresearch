# LLM Safety Concerns

## Hallucination

Hallucination is one of the most significant safety concerns with large language models. Models generate plausible-sounding but factually incorrect information with high confidence. This is particularly dangerous in domains like healthcare, legal advice, and financial guidance where incorrect information can cause real harm.

## Jailbreak Attacks

Jailbreak attacks bypass safety guardrails through adversarial prompting techniques. Attackers craft prompts that trick the model into ignoring its safety training and producing harmful content. Common techniques include role-playing scenarios, encoding obfuscation, and multi-turn conversation exploits that gradually erode safety boundaries.

## Bias and Fairness

Bias in training data leads to discriminatory or unfair model outputs. Language models reflect and sometimes amplify societal biases present in their training corpora. This manifests as stereotypical associations, unequal representation, and differential performance across demographic groups.

## Privacy Risks

LLMs can memorize and regurgitate personally identifiable information from training data. Prompt injection attacks can manipulate models to reveal sensitive information or perform unintended actions in agentic deployments.
