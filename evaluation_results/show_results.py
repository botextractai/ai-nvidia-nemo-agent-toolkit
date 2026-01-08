import json

with open('evaluation_results/answer_accuracy_output.json', 'r') as f:
    answer_accuracy_data = json.load(f)

print(f"📊 Evaluation Results")
print(f"=" * 50)
print(f"Average Score: {answer_accuracy_data['average_score']} / 1.0")
print()

for item in answer_accuracy_data['eval_output_items']:
    r = item['reasoning']
    print(f"❓ {r['user_input']}")
    print(f"✅ Expected: {r['reference']}")
    print(f"💬 Got: {r['response']}")
    print(f"📈 Score: {item['score']}")
    print()
