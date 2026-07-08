# 참고문헌 후보 정리

## 목적

이 문서는 영문 SCIE/IEEE Access 원고 작성 전에 참고문헌을 어디서 가져와야 하는지 정리한 목록이다. 참고문헌은 블로그나 일반 소개 글보다 논문, 공식 기술 보고서, 공식 문서를 우선한다.

## 참고문헌 선정 기준

- RAG, dense retrieval, multimodal retrieval의 핵심 원 논문을 우선 사용한다.
- 실제 시스템에서 사용한 모델이나 도구는 공식 논문, 기술 보고서, 공식 문서를 사용한다.
- 협동 로봇 실습 교육 관련 배경은 hands-on curriculum, collaborative robotics training 관련 학술 자료를 사용한다.
- 개인 블로그, Medium, Reddit, 단순 요약 자료는 본문 참고문헌으로 사용하지 않는다.

## 1. RAG 및 검색 기반 참고문헌

| 번호 | 문헌 | 사용할 위치 | 이유 |
|---|---|---|---|
| R1 | Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," NeurIPS, 2020 | Introduction, Related Work | RAG의 대표 원 논문 |
| R2 | Karpukhin et al., "Dense Passage Retrieval for Open-Domain Question Answering," EMNLP, 2020 | Related Work, Method | dense retrieval의 대표 기준 논문 |
| R3 | Robertson and Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond," 2009 | Experiment Setup | G1 keyword/BM25 계열 baseline 설명 |
| R4 | Chen et al., "BGE M3-Embedding," ACL Findings, 2024 | Method | BGE-M3 텍스트 임베딩 근거 |

## 2. 멀티모달 및 이미지-텍스트 임베딩 참고문헌

| 번호 | 문헌 | 사용할 위치 | 이유 |
|---|---|---|---|
| M1 | Radford et al., "Learning Transferable Visual Models From Natural Language Supervision," ICML, 2021 | Related Work | CLIP 기반 image-text retrieval 배경 |
| M2 | Zhai et al., "Sigmoid Loss for Language Image Pre-Training," 2023 | Related Work, Method | SigLIP 사용 근거 |

## 3. 로컬 LLM 및 양자화 참고문헌

| 번호 | 문헌 | 사용할 위치 | 이유 |
|---|---|---|---|
| L1 | Qwen Team, "Qwen2.5 Technical Report," 2024 | Experimental Setup | Qwen 2.5 모델 근거 |
| L2 | Gemma Team, "Gemma 2: Improving Open Language Models at a Practical Size," 2024 | Experimental Setup | Gemma 2 모델 근거 |
| L3 | Meta AI, "The Llama 3 Herd of Models," 2024 | Experimental Setup | Llama 3.1 모델 근거 |
| L4 | Dettmers et al., "QLoRA: Efficient Finetuning of Quantized LLMs," NeurIPS, 2023 | Method 또는 Discussion | 4-bit quantization 설명 배경 |

## 4. 시스템 구현 도구 참고문헌

| 번호 | 문헌 | 사용할 위치 | 이유 |
|---|---|---|---|
| T1 | Chroma official documentation | Method, Experimental Setup | ChromaDB 벡터 저장소 설명 |
| T2 | Doosan Robotics User Manual / DART-Platform Manual | Dataset | 실험 데이터 출처 |

## 5. 협동 로봇 실습 교육 참고문헌

| 번호 | 문헌 | 사용할 위치 | 이유 |
|---|---|---|---|
| C1 | Djuric et al., "Hands-On Learning Environment and Educational Curriculum on Collaborative Robotics," ASEE, 2017 | Introduction, Related Work | 협동 로봇 교육에서 hands-on curriculum 필요성 근거 |
| C2 | Didactic Design of a Remote Collaborative Robotics Laboratory | Related Work | 원격/실습형 collaborative robotics lab 배경 후보 |
| C3 | Introducing Novice Operators to Collaborative Robots | Related Work | 초보자를 위한 cobot training 배경 후보 |

## 현재 초안에 우선 반영한 문헌

현재 `19_paper_draft.md`에는 다음 문헌을 우선 반영했다.

| 초안 번호 | 문헌 |
|---|---|
| [1] | RAG 원 논문 |
| [2] | DPR |
| [3] | BM25 |
| [4] | BGE-M3 |
| [5] | CLIP |
| [6] | SigLIP |
| [7] | Qwen2.5 |
| [8] | Gemma 2 |
| [9] | Llama 3 |
| [10] | QLoRA |
| [11] | Chroma |
| [12] | Collaborative robotics hands-on curriculum |
| [13] | Doosan Robotics DART-Platform Manual |

## 추가 확인이 필요한 문헌

다음 문헌은 본문에 넣기 전에 서지정보를 더 확인해야 한다.

- Didactic Design of a Remote Collaborative Robotics Laboratory
- Introducing Novice Operators to Collaborative Robots
- Collaborative robot education 또는 engineering education 관련 최신 survey

이 문헌들은 협동 로봇 교육 배경을 강화할 때 사용할 수 있다. 다만 현재 논문의 핵심 기여는 RAG 검색 구조와 실험 결과이므로, 관련 연구 섹션에서 너무 많은 교육학 문헌을 넣기보다 2~3개 정도만 사용하는 것이 적절하다.

## 참고문헌 작성 시 주의사항

- IEEE 원고에서는 최종적으로 `[1]`, `[2]` 형식으로 번호를 정리한다.
- arXiv 문헌은 가능하면 학회/저널 출판본이 있는지 확인한 뒤 최종 형식을 정한다.
- 공식 문서는 논문보다 우선순위가 낮지만, ChromaDB와 Doosan 매뉴얼처럼 시스템 구현이나 데이터 출처를 설명할 때는 사용할 수 있다.
- 현재 로컬 LLM 모델은 Qwen 2.5 7B, Gemma 2 9B, Llama 3.1 8B를 기준으로 하므로, 각 모델의 공식 기술 보고서를 함께 인용하는 것이 좋다.
