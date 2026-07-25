# Manuscript Draft v1.1 - English Version

> This document is the English manuscript draft prepared from the Korean working draft for a prospective SCIE/IEEE Access submission.
> The quantitative results, evaluation criteria, figures, and stated limitations are preserved from the Korean draft.

## Title

**A Context-Aware Multimodal Retrieval-Augmented Generation Framework for Collaborative Robot Training**

Alternative title:

**Improving Multimodal Retrieval for Collaborative Robot Training Using Context-Aware Retrieval-Augmented Generation**

## Abstract

Collaborative robot training requires learners to jointly interpret procedural descriptions, configuration values, safety conditions, images, and diagrams provided in technical manuals. Conventional text retrieval and text-only retrieval-augmented generation (RAG) systems, however, make limited use of visual materials such as training screens, wiring diagrams, and configuration interfaces. They also have difficulty prioritizing information that corresponds to the learner's current training stage. This study proposes a context-aware multimodal RAG framework for collaborative robot training. The proposed system separately indexes text chunks and visual materials extracted from a collaborative robot manual. During preprocessing, bounding-box (BBox) distance is used as a spatial candidate filter, and text-image pairs that pass the filter are ranked using SigLIP semantic similarity to generate mapping metadata. The mapping metadata is then combined with text retrieval, image-only retrieval, and page proximity. The system also estimates the training stage from the user query and re-ranks candidates using a context map composed of stage-specific page ranges, section headings, and keywords. The framework is designed to reduce dependence on external application programming interfaces by using a local vector database and a 4-bit quantized large language model (LLM), with offline operation on resource-constrained devices, including systems with approximately 8 GB of RAM, as a design objective. This hardware target is not treated as a primary quantitative result; runtime and memory measurements on an actual system with 8 GB or less remain to be validated.

For evaluation, a set of 70 queries was constructed from a collaborative robot training manual, and each query was annotated with a relevant text answer, a ground-truth image, and a training-stage label. Four retrieval groups were compared: keyword-based retrieval (G1), text-only RAG (G2), multimodal RAG (G3), and stage-estimation-based context-aware multimodal RAG (G4). Compared with G3, G4 increased Image Recall@5 from 74.3% to 85.7%, Image Recall@10 from 84.3% to 92.9%, and Image MRR from 0.534 to 0.608. Image Recall@1 also increased from 38.6% to 44.3%. These results indicate that stage-aware context re-ranking can move relevant images and diagrams to higher positions in the candidate ranking. Nevertheless, Image Recall@1 remained below 50%, indicating that the proposed method does not fully solve fine-grained image retrieval. In addition, response quality did not improve consistently across all language models. Accordingly, the principal contribution of this study is limited to improving context-aware multimodal retrieval rather than generation quality. Remaining limitations include errors in query-based stage estimation and difficulty distinguishing visually similar images located on the same page or within the same section.

## Keywords

Collaborative robot training, multimodal RAG, retrieval-augmented generation, context-aware retrieval, engineering education, robot manual retrieval

## 1. Introduction

Collaborative robots are used in manufacturing, education, and research environments where humans and robots share a workspace. In engineering education, learners can practice procedures such as robot installation, coordinate configuration, safety configuration, direct teaching, and program execution.

The collaborative robot training manual analyzed in this study distributes procedural descriptions, teach pendant screens, wiring diagrams, and safety configuration images across multiple pages. To identify information relevant to a particular training situation, learners must examine not only menu names and configuration items but also screen locations and associated images. Novice learners may also have difficulty connecting their current training stage to the corresponding section of the manual.

Retrieval-augmented generation (RAG) uses evidence retrieved from external documents to support language-model response generation [1]. Conventional text-only RAG primarily retrieves text chunks and may therefore provide a limited range of evidence for documents in which images, diagrams, and screen examples are necessary to understand a procedure. Because text and visual materials play complementary roles in collaborative robot training manuals, text retrieval alone may be insufficient to construct the required evidence.

To address this limitation, this study proposes a context-aware multimodal RAG framework for collaborative robot training. The proposed system jointly retrieves text and visual materials from a manual and uses training-stage context to adjust their ranking. The central contribution is not an improvement in final answer generation itself, but the retrieval of more appropriate textual evidence and visual materials before answer generation.

The main contributions of this study are as follows.

1. A 70-query evaluation set was constructed from a collaborative robot training manual, with annotations for relevant text, ground-truth images, and training stages.
2. An experimental framework was designed to compare keyword retrieval, text-only RAG, multimodal RAG, and context-aware multimodal RAG using the same query set.
3. A multimodal retrieval architecture was implemented in which BBox distance serves as a spatial candidate filter and SigLIP semantic similarity serves as a candidate-ranking signal. The resulting text-image mapping is combined with text retrieval, image-only retrieval, and page proximity.
4. Query-based training-stage estimation and a stage-specific context map were applied to re-ranking, and their effects on image and diagram ranking and Both@k performance were evaluated.
5. Response quality was evaluated as a separate outcome, and representative improved and failed cases were examined to clarify the benefits and limitations of context-aware multimodal retrieval.

## 2. Related Work

### 2.1 Retrieval-Augmented Generation

RAG supplements the parametric knowledge of an LLM with evidence retrieved from external documents [1]. A typical RAG pipeline divides documents into chunks, embeds each chunk, and stores the resulting representations in a vector database. When a user submits a query, the system compares the query embedding with document embeddings, retrieves relevant chunks, and supplies them to the language model as context for answer generation.

Retrieval methods used in RAG can broadly be divided into sparse and dense retrieval. BM25 is widely used as a representative keyword-based sparse retrieval baseline [3], whereas Dense Passage Retrieval (DPR) represents questions and passages using dense vectors [2]. In this study, G1 serves as the keyword-based baseline, while G2 implements dense retrieval using BGE-M3 embeddings [4].

RAG is useful for documents with well-defined domain knowledge, such as technical manuals, internal documentation, and educational materials. Text-only RAG, however, relies mainly on sentence- or paragraph-level text retrieval and is therefore limited when documents depend heavily on images, diagrams, tables, and screen captures. Collaborative robot training manuals are a representative example of this document type.

### 2.2 Multimodal Retrieval

Multimodal retrieval uses information from different modalities, such as text, images, diagrams, and audio, to identify relevant evidence. Vision-language models that map images and text into a shared embedding space enable text-to-image retrieval and image-text association. CLIP is a representative vision-language model trained with natural-language supervision [5], while SigLIP introduces sigmoid-loss-based image-text pretraining [6]. In this study, CLIP is discussed as related work, whereas SigLIP is the vision-language model used to compute text-image semantic similarity.

Training manuals frequently describe a single procedure using both text and images. A menu path may be explained in text, while the learner must also inspect a teach pendant or configuration screen. Independently returning text and image search results is therefore insufficient. A retrieval system must also consider how textual and visual materials are connected by page layout, surrounding context, and training stage.

### 2.3 Context-Aware Retrieval for Training Guidance

Queries in a practical training environment may be associated with particular task stages. Even when two queries contain similar terms, the required evidence and related image may differ depending on whether the learner is performing installation, configuring safety settings, or executing a program. Prior work on collaborative robot education has discussed the importance of laboratory practice and training modules involving safety, operation, and programming [12]. Retrieval for training guidance should therefore consider the training stage and manual structure in addition to semantic query similarity.

This study estimates the training stage from the query and uses a context map containing stage-specific page ranges, section headings, and keywords to re-rank multimodal retrieval results.

## 3. Proposed Framework

### 3.1 Overall Architecture

The proposed system preprocesses textual and visual materials extracted from a collaborative robot training manual and indexes them for retrieval. When a user submits a training-related query, the system retrieves relevant text chunks and image candidates and generates a response using a selected local LLM.

The overall pipeline consists of the following steps.

1. Text and visual materials are extracted from the manual PDF.
2. Text is divided into chunks while retaining page numbers, section information, surrounding context, and text BBoxes.
3. Each extracted image is stored with its page number and image BBox.
4. Text-image pairs are collected from the same page and the following page. BBox distance restricts the spatial candidate set, and SigLIP semantic similarity ranks the remaining candidates to generate mapping metadata.
5. Text embeddings, the image index, and text-image mapping metadata are stored locally.
6. Text and image candidates are retrieved for the user query.
7. G3 combines text retrieval, image retrieval, page proximity, and precomputed SigLIP-based text-image mapping scores.
8. G4 estimates the training stage from the query and adjusts the candidate ranking using the corresponding context map.
9. The local LLM generates training guidance from the retrieved evidence.

### 3.2 Text Preprocessing and Indexing

Text extracted from the manual is divided into chunks while preserving procedural and semantic units. Each chunk stores the original text, page number, section-related metadata, and the BBox coordinates of the corresponding text region. A BBox represents the rectangular region occupied by text on a PDF page as `(x0, y0, x1, y1)`. BGE-M3 is used to generate text embeddings, and ChromaDB is used as the vector database.

In G2, the top-k text candidates are retrieved using the similarity between the query embedding and text-chunk embeddings. These candidates provide evidence for LLM-based answer generation.

### 3.3 Image and Diagram Preprocessing and Retrieval

Images and diagrams extracted from the manual are managed using their filenames, page numbers, and image BBoxes. Because an isolated image may have limited semantic information, spatial and semantic associations between text chunks and images are computed during preprocessing. For each text chunk, images on the same page and the following page are collected as initial candidates. On the same page, the two-dimensional distance between the grouped text BBox and the center of the image BBox is calculated. The distance is adjusted to reflect the common manual layout in which an image appears below the corresponding text. A spatial penalty is applied to candidates on the following page.

BBox distance is not directly added to the final mapping score; it is used only as a candidate gate. Images with an adjusted distance below 300 points are retained as spatial candidates. To avoid discarding semantically related images with distant layouts, candidates are also rescued when the robust-normalized SigLIP similarity is at least 0.40. Candidate ranking and the `mapping_score` are determined using SigLIP image-text cosine similarity. The cosine values are normalized to the range of 0 to 1 using robust boundaries derived from the preprocessing-pair distribution, and the same fixed boundaries are applied to the full dataset. BBox therefore removes spatially distant images, whereas SigLIP ranks the retained candidates by semantic relevance. These computations are performed once during offline preprocessing; the application uses only the stored mappings at runtime.

G3 combines the following signals for image retrieval:

- image-only retrieval score;
- proximity between retrieved text pages and image pages;
- precomputed SigLIP text-image mapping score after BBox candidate filtering; and
- baseline candidate-rank score.

This design retrieves not only textual evidence directly related to the query but also visual materials that are spatially and semantically connected to that evidence. Figure 1 presents the overall system architecture, including BBox filtering and SigLIP-based mapping. Figure 2 presents the G4 candidate expansion and re-ranking process that applies automatically inferred stage context to the G3 candidates.

### 3.4 Context-Aware Re-Ranking

G4 extends G3 by adding training-stage estimation and context-map-based re-ranking. For each training stage, the context map contains relevant page ranges, section headings, keywords, and mapping rationale. It was manually reviewed using the semantic structure of the manual and the meaning of each training stage. Ground-truth image filenames and ground-truth chunk identifiers were not used in the context map.

G4 performs re-ranking as follows.

1. BGE-M3 semantic similarity is computed between the query and each training-stage context profile to estimate the most relevant stage.
2. If the highest stage similarity is below 0.45 or the similarity margin between the first- and second-ranked stages is below 0.03, the system does not apply G4 re-ranking and instead falls back to the G3 ranking.
3. The page ranges and keywords associated with the estimated stage are loaded.
4. An additional score is assigned when a candidate falls within the relevant page range.
5. The score is adjusted when the surrounding text or section information matches the stage-specific keywords.
6. The G3 retrieval score and context score are combined to calculate the final ranking.

This procedure does not directly select candidates using ground-truth labels. Instead, it prioritizes candidates according to the manual structure and inferred training-stage context, and can therefore be interpreted as context-aware retrieval.

**Algorithm 1. Context-aware multimodal re-ranking in G4**

```text
Input: query q; G3 text candidates T; G3 image candidates I;
       stage profiles S; stage context map C; text/image return sizes k_T, k_I
Output: re-ranked text candidates T' and image candidates I'
Parameters: tau_s=0.45, tau_m=0.03, beta_t=0.28,
            lambda_c=0.50, lambda_p=0.25, R=120

1:  e_q <- BGE-M3(q)
2:  For each stage s in S, compute a_s <- cos(e_q,e_s).
3:  Let s* <- argmax_s(a_s), with the two highest similarities a_1 >= a_2.
4:  if a_1 < tau_s or (a_1-a_2) < tau_m then
5:      return G3-TopK(T,k_T), G3-TopK(I,k_I)
6:  Load text/image page ranges, keywords, section terms, and stage weight
    w_s from c* <- C[s*]; add valid images in the stage image range to I.
7:  for each text candidate t in T do
8:      (p_t,k_t,h_t) <- StageMatch(t,c*)
9:      c_t <- w_s(0.55p_t + 0.30k_t + 0.15h_t)
10:     b_t <- 1-(r_G3(t)-1)/|T|;  f_t <- b_t + beta_t c_t
11: for each image candidate i in I do
12:     b_i <- 0.25v_i + 0.15l_i + 0.50n_i + 0.05m_i + 0.05d_i
13:     (p_i,k_i,h_i) <- StageMatch(i,c*)
14:     c_i <- w_s(0.50p_i + 0.10k_i + 0.40h_i)
15: Sort all image candidates by b_i to obtain the baseline rank r_B(i).
16: for each image candidate i in I do
17:     if r_B(i) <= R: rho_i <- 1-(r_B(i)-1)/R
18:     else if p_i > 0: rho_i <- 0.35; else: rho_i <- 0
19:     f_i <- b_i + lambda_c c_i rho_i + lambda_p p_i
20: Sort T by f_t and I by f_i in descending order.
21: return TopK(T,k_T), TopK(I,k_I)
```

In Algorithm 1, `T` denotes the G3 text list expanded to at most 30 candidates when G4 is activated. `I` is the union of text-linked images, adjacent-page images, image-index candidates, and valid images within the inferred stage page range. `S` denotes the stage profiles constructed from stage names, section terms, content/action keywords, and manual evidence, whereas `C` stores the text and image page ranges and terms associated with each stage. `a_1` and `a_2` are the highest and second-highest cosine similarities between the query and stage profiles.

For a candidate `x`, `p_x`, `k_x`, and `h_x` denote stage-page, keyword, and section-heading match scores, respectively. The page score is 1.0 within the mapped range, 0.70 at a one-page distance, 0.45 at a two-page distance, and 0 otherwise. Keyword and section scores are normalized to the range [0,1] using matched terms in the candidate metadata. For an image candidate, `v_i`, `l_i`, `n_i`, `m_i`, and `d_i` denote image-only retrieval, linked-text rank, page proximity, stored SigLIP mapping after BBox candidate filtering, and diagram confidence, respectively. `b_x`, `c_x`, and `f_x` are the baseline, stage-context, and final scores. The attenuation factor `rho_i` prevents the context term from excessively promoting images that have weak baseline evidence.

If `a_1` is below `tau_s` or the difference between the two highest stage similarities is below `tau_m`, stage estimation is treated as insufficiently reliable and the method falls back to the G3 ranking. The thresholds and weights in Algorithm 1 are fixed for all queries, and their selection procedure is described in Section 4.4. To control experimental leakage, context map `C` contains no query IDs, ground-truth image filenames, or ground-truth chunk identifiers.

### 3.5 Local LLM Response Generation and Resource-Constrained Design

The system uses local LLMs to support deployment in resource-constrained environments. The implementation allows responses to be generated and compared using models from the Qwen, Gemma, and Llama families. Retrieved textual evidence and image-candidate information are supplied as context for generating training guidance.

For offline operation, the application uses Ollama-hosted local models and does not call an external LLM API at runtime. The selected models are 7B-9B Q4-quantized models, which reduce local storage and memory requirements. BBox distance and SigLIP text-image similarity are computed during preprocessing, while runtime retrieval uses the stored indexes and mapping metadata. This configuration is intended to provide both textual evidence and related images without relying on a cloud-based model.

The quantitative evaluation focuses on the retrieval performance of G1-G4; offline execution speed and system performance in an 8 GB RAM environment were not measured. The resource-constrained configuration should therefore be interpreted as a design objective rather than a validated minimum hardware specification.

Response quality was evaluated separately from retrieval performance. A rule-based rubric evaluation was applied to all responses using correctness, specificity, training-stage relevance, safety, and comprehensibility criteria. Section 6 describes the evaluation criteria and procedure.

## 4. Experimental Design

### 4.1 Dataset

The experimental dataset was constructed from a collaborative robot training manual. A total of 70 queries were created, and each query was annotated with relevant text, a ground-truth image, and a training-stage label. The queries cover procedures frequently encountered in collaborative robot training, including installation, power supply, teach pendant operation, direct teaching, coordinate configuration, safety configuration, I/O wiring, and system management.

The query set was designed to emphasize questions for which a ground-truth image could be clearly identified, enabling quantitative evaluation of multimodal image retrieval.

### 4.2 Comparison Groups

The experiment compared the following four groups.

| Group | Name | Description |
|---|---|---|
| G1 | Keyword Search | Retrieves text chunks based on keyword overlap with the query |
| G2 | Text-only RAG | Retrieves text chunks using BGE-M3 text embeddings |
| G3 | Multimodal RAG | Combines text retrieval, image retrieval, page proximity, and BBox-filtered SigLIP text-image mapping |
| G4 | Context-aware Multimodal RAG | Estimates the training stage from the query and applies context-map-based re-ranking to G3 candidates |

G1 and G2 serve as baselines for text retrieval. G3 adds image and diagram retrieval, while G4 is the proposed method that incorporates training-stage information to re-rank multimodal candidates.

### 4.3 Evaluation Metrics

Retrieval performance was evaluated using Recall@k and mean reciprocal rank (MRR).

Text Recall@k measures the proportion of queries for which the top-k text candidates contain the relevant text or equivalent information. Image Recall@k measures the proportion of queries for which the top-k image candidates contain the ground-truth image. MRR evaluates how highly the first relevant candidate is ranked. From a multimodal perspective, Both@k measures whether both the relevant text and ground-truth image are present within their respective top-k results.

Text retrieval was evaluated using a relaxed relevance criterion. A retrieved text candidate was considered relevant if it was located on the same page or in the same section as the reference evidence, contained essential keywords from the reference answer, or conveyed semantically equivalent procedural or configuration information. This criterion was adopted because procedural information in the manual may be distributed across adjacent chunks or multiple passages on the same page rather than appearing in a single fixed sentence.

Image retrieval was evaluated using strict filename matching. An image was considered correct only when the exact ground-truth filename appeared among the top-k image candidates. A visually similar image from the same page was counted as incorrect if its filename differed. Consequently, Text Recall@k and Text MRR in this paper represent relaxed text retrieval performance, whereas Image Recall@k and Image MRR represent strict image retrieval performance. Both@k requires a relaxed text hit and a strict image hit simultaneously.

| Metric | Relevance Criterion |
|---|---|
| Text Recall@k / Text MRR | Relaxed: at least one of page/section agreement, essential-keyword inclusion, or semantic equivalence |
| Image Recall@k / Image MRR | Strict: the exact ground-truth image filename must appear in the top-k results |
| Both@k | A relaxed text hit and a strict image hit must both be satisfied |

### 4.4 Retrieval Score Composition and Weight Selection

The baseline G3 image score is a weighted sum of image-only retrieval (0.25), text-candidate rank (0.15), page proximity between the retrieved text and image (0.50), precomputed SigLIP mapping (0.05), and diagram confidence (0.05). BBox distance is not included in this weighted sum and is used only as a preprocessing candidate filter. The G4 image context score is composed of page (0.50), keyword (0.10), and section (0.40) scores. The final G4 image score additionally includes the context score with a weight of 0.50 and a stage-page prior with a weight of 0.25. A rank factor that decreases with the baseline G3 rank is applied to the context term. A factor of 0.35 is used for candidates outside the top 120 baseline ranks when they fall within the inferred stage page range. For text re-ranking, 0.28 times the stage-context score is added to the baseline retrieval-rank score.

Using the notation in Algorithm 1, the minimum stage similarity `tau_s` is 0.45, the minimum margin `tau_m` is 0.03, the text-context coefficient `beta_t` is 0.28, the image-context coefficient `lambda_c` is 0.50, the stage-page prior coefficient `lambda_p` is 0.25, and the baseline-rank attenuation window `R` is 120. These values are fixed implementation parameters applied uniformly to all evaluated queries rather than query-specific settings.

The weights were compared through a limited grid search using a candidate-level feature cache generated from the 70 queries. Strict Image MRR was used as the primary selection criterion, with Recall@5 and Recall@10 as secondary metrics. Five-fold cross-validation was also used to examine fold-level stability. In the sensitivity analysis, a mixture of 0.1 BBox and 0.9 SigLIP yielded the highest MRR, whereas the BBox-only setting produced lower Recall@5 and Recall@10 and the effect of the BBox ratio was not consistent across all metrics. The final system therefore separates the two signals by using BBox for spatial candidate filtering and SigLIP for semantic ranking. This design choice should not be interpreted as an independently validated optimum. Because weight selection and final evaluation used the same 70-query internal pilot dataset, a separate hold-out set or evaluation using an additional manual remains necessary.

The following compact comparison fixes the remaining G3 retrieval components and varies only the text-image mapping design. It is presented as a supporting analysis for separating the roles of BBox and SigLIP rather than as an independent evaluation of the two components.

| Text-Image Mapping Configuration | Image R@1 | Image R@5 | Image R@10 | Image MRR |
|---|---:|---:|---:|---:|
| BBox 0.0 + SigLIP 1.0 | 34.3% | 77.1% | **87.1%** | 0.521 |
| BBox 0.1 + SigLIP 0.9 | **38.6%** | **77.1%** | 85.7% | **0.546** |
| BBox 1.0 + SigLIP 0.0 | 37.1% | 72.9% | 81.4% | 0.515 |

### 4.5 Experimental Environment

The experiments were performed on a local laptop. Although the study targets an offline RAG system that can operate under constrained resources, the current quantitative experiments were conducted on the development and evaluation machine described below. The approximately 8 GB RAM target is therefore presented as a design and model-selection objective. Runtime, memory consumption, and concurrent stability on an actual system with 8 GB or less remain part of future reproducibility validation. The retrieval and response-quality tables reported in this paper compare groups under the same development environment and are not benchmarks measured on an 8 GB RAM device.

| Item | Specification |
|---|---|
| Operating system | Windows |
| Device | HP OMEN Gaming Laptop 16-am0xxx |
| CPU | Intel Core Ultra 7 255H, 16 cores / 16 logical processors |
| RAM | Approximately 24 GB |
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU and Intel Graphics |
| Python | 3.12.10 (.venv) |
| Vector database | ChromaDB 1.5.9 |
| Application framework | Streamlit 1.58.0 |
| Embedding / ML stack | sentence-transformers 5.6.0, transformers 5.12.1, torch 2.12.1 |
| Data processing | pandas 3.0.3, PyMuPDF 1.27.2.3, Pillow 12.2.0 |

The local LLMs were configured to run through Ollama. The primary models used by the comparison applications are listed below.

| Model | Local Model ID | Application File | Local Storage Size |
|---|---|---|---:|
| Qwen 2.5 7B Q4 | qwen2.5:7b | src/app_qwen.py | Approximately 4.36 GB |
| Gemma 2 9B Q4 | gemma2:9b | src/app_gemma.py | Approximately 5.07 GB |
| Llama 3.1 8B Q4 | llama3.1:8b | src/app_llama.py | Approximately 4.58 GB |

Other locally stored models were excluded from the comparison. The primary comparison was limited to Qwen 2.5 7B, Gemma 2 9B, and Llama 3.1 8B.

## 5. Experimental Results

### 5.1 Overall Retrieval Performance

Table I summarizes the final text, image, and joint retrieval performance of G1, G2, G3, and G4 under the current implementation.

| Group | Text R@1 | Text R@5 | Text R@10 | Text MRR | Image R@1 | Image R@5 | Image R@10 | Image MRR | Both@5 | Both@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G1 Keyword Search | 75.7% | 92.9% | 98.6% | 0.827 | - | - | - | - | - | - |
| G2 Text-only RAG | 78.6% | 94.3% | 100.0% | 0.859 | - | - | - | - | - | - |
| G3 Multimodal RAG | 78.6% | 94.3% | 100.0% | 0.859 | 38.6% | 74.3% | 84.3% | 0.534 | 74.3% | 84.3% |
| G4 Context-aware Multimodal RAG | 84.3% | 95.7% | 100.0% | 0.894 | 44.3% | 85.7% | 92.9% | 0.608 | 84.3% | 92.9% |

Despite being a simple keyword-based method, G1 achieved a Text Recall@5 of 92.9%. This can be attributed to the explicit technical terms in collaborative robot manual queries, including menu names, configuration values, and function names. G2 nevertheless outperformed G1 in Text Recall@1 and Text MRR, indicating that embedding-based text retrieval was more effective at placing the relevant text at a higher rank.

G2 and G3 produced identical text retrieval results because both groups use the same BGE-M3 text embedding model, ChromaDB text collection, text chunks, and top-k text retrieval procedure. G3 does not modify the G2 text retriever; instead, it extends the G2 results with image-only retrieval, page proximity, and text-image mapping scores. The identical Text Recall@k and Text MRR values are therefore an intended consequence of the experimental design rather than an implementation error. G3 is evaluated for its ability to retrieve relevant images and diagrams in addition to text, not for improving text retrieval.

G3 achieved an Image Recall@5 of 74.3% and an Image Recall@10 of 84.3%, while Image Recall@1 and Image MRR were 38.6% and 0.534, respectively. Using BBox as a candidate filter and combining SigLIP mapping with page proximity still placed the ground-truth image at rank one for fewer than half of the queries.

G4 produced numerically higher image-retrieval metrics than G3. Image Recall@5 increased from 74.3% to 85.7%, Image Recall@10 increased from 84.3% to 92.9%, and Image MRR increased from 0.534 to 0.608. Both@5 and Both@10 likewise increased from 74.3% to 84.3% and from 84.3% to 92.9%, respectively. Image Recall@1 increased by 5.7 percentage points, from 38.6% to 44.3%. These results indicate that G4 moved some relevant images into the top-five or top-ten range and improved their average rank rather than consistently placing the ground-truth image at rank one. Because no statistical significance test was included, these numerical increases should not be interpreted as evidence of general superiority.

### 5.2 Cases Improved by G4

Aggregate metrics do not fully explain how G4 changes the candidate ranking. This subsection therefore examines queries for which the ground-truth image rank improved relative to G3. These cases demonstrate how query-based stage estimation, page ranges, section headings, and keyword context can move relevant images upward.

For Q31, which asks about the primary purpose of the USB port on the teach pendant, the ground-truth image `page_103_img_0_0.jpeg` moved from rank eight in G3 to rank three in G4. The query was associated with the `teach pendant/USB data management` stage, and the context included terms related to USB ports, the pendant, and data import/export.

For Q23, which asks where to check the system time, the ground-truth image `page_167_img_3_0.jpeg` was outside the top ten in G3 but moved to rank four in G4. The query was associated with the `UI/system information inspection` stage, and context related to system information, time, and screen areas contributed to re-ranking.

For Q02, which asks about the grounding conditions required to supply power to the controller, the ground-truth image `page_403_img_0_0.jpeg` moved from rank two in G3 to rank one in G4. The query was associated with the `safety/power/grounding` stage, and context involving grounding, power supply, the controller, and safety was applied.

These cases show that G4 can use training-stage information to improve the rank of the correct image for some queries. They do not, however, imply consistent top-one retrieval across the full query set.

### 5.3 Failure Cases of G4

Reporting only improved cases would overstate the effectiveness of G4. The following failures demonstrate that page- and section-level context does not fully resolve ambiguity among similar images, compensate for missing fine-grained screen cues, or eliminate query-based stage-estimation errors.

Q10 asks for the menu path used to inspect the current angle of each robot joint on the teach pendant. Although G4 considered Status-related pages and keywords, it failed to retrieve the ground-truth image `page_332_img_0_0.jpeg` within the top ten. Terms such as `Status`, `I/O Overview`, and `joint angle` did not contribute strongly enough during candidate collection.

Q28 asks which cable-coupling component is required to strengthen the waterproof rating of the robot cube module cable. G4 moved several images near page 405 upward, but the exact ground-truth image `page_405_img_0_0.jpeg` remained outside the top ten. This case reveals insufficient image-level discrimination among multiple images on the same page.

Q15 asks for the menu path used to export historical system error logs. The stage estimator favored `UI/system information inspection` rather than `system management/logs`, and the ground-truth image `page_340_img_0_0.jpeg` did not appear within the top ten. This case demonstrates that G4 performance depends on the accuracy of stage estimation.

These failures also clarify the role of the BBox candidate filter. BBox is useful for eliminating spatially distant images, but it does not distinguish similar images that pass the filter on the same page. The current ranking therefore depends on SigLIP semantic similarity and page- and section-level context, which may not capture small differences within a screen or the ordering of multiple images. Image captions, local text surrounding each image BBox, image-order information, and more fine-grained stage labels are possible directions for addressing this limitation.

## 6. Response Quality Evaluation

Retrieval performance and local-LLM response quality were evaluated as distinct outcomes. Responses were generated under G2, G3, and G4 using Qwen, Gemma, and Llama, yielding 630 responses across 70 queries.

Response quality was assessed using the following five criteria.

1. Correctness: Does the response agree with the essential content of the reference answer?
2. Specificity: Does the response provide sufficiently specific menu paths, button names, configuration values, or procedures?
3. Training-stage relevance: Is the guidance appropriate for the training stage represented by the query?
4. Safety: Does the response avoid unsafe or incorrect robot-operation instructions?
5. Comprehensibility: Is the explanation understandable to a novice learner?

Each criterion was scored from 1 to 5, and the average was used to compare models and retrieval groups. All 630 responses were processed using a rule-based rubric based on reference-keyword agreement, semantic similarity, and safety and readability rules.

| Group | Model | N | Mean Score | O | Partial | X |
|---|---|---:|---:|---:|---:|---:|
| G2 Text-only RAG | Qwen | 70 | 4.05 | 49 | 13 | 8 |
| G2 Text-only RAG | Gemma | 70 | 3.59 | 27 | 31 | 12 |
| G2 Text-only RAG | Llama | 70 | 3.62 | 24 | 33 | 13 |
| G3 Multimodal RAG | Qwen | 70 | 4.01 | 47 | 15 | 8 |
| G3 Multimodal RAG | Gemma | 70 | 3.56 | 27 | 29 | 14 |
| G3 Multimodal RAG | Llama | 70 | 3.60 | 28 | 27 | 15 |
| G4 Context-aware Multimodal RAG | Qwen | 70 | 3.99 | 47 | 14 | 9 |
| G4 Context-aware Multimodal RAG | Gemma | 70 | 3.59 | 27 | 31 | 12 |
| G4 Context-aware Multimodal RAG | Llama | 70 | 3.62 | 31 | 26 | 13 |

Qwen achieved higher mean scores than the other two models in all three retrieval groups. Unlike retrieval performance, however, response quality did not improve consistently under G4. Qwen achieved mean scores of 4.05 in G2, 4.01 in G3, and 3.99 in G4, indicating a small decrease under G4. Gemma increased slightly from 3.56 in G3 to 3.59 in G4, while Llama increased from 3.60 to 3.62.

These results show that a numerical increase in retrieval performance did not directly translate into improved response quality. Generated responses were jointly affected by changes in the retrieved evidence, query-based stage estimation, and the generation characteristics of each local LLM. The contribution of this study should therefore be interpreted as a limited improvement at the retrieval stage. This rule-based response-quality evaluation does not substitute for judgments by users or domain experts and is not used as evidence of educational effectiveness.

## 7. Discussion

G1 already achieved a high Text Recall@5, and G2 and G3 reached a Text Recall@10 of 100.0%. In contrast, G3 achieved an Image Recall@1 of 38.6%. However, text retrieval used a relaxed relevance criterion, whereas image retrieval used strict filename matching. The absolute values of the two modalities therefore cannot be directly compared to conclude that image retrieval is inherently more difficult. Nevertheless, under the strict criterion, the ground-truth image was ranked first for fewer than half of the queries, indicating that image ranking remains a major target for improvement.

G4 achieved numerically higher Image Recall@5, Image Recall@10, and Image MRR than G3. In several cases with clearly defined stage-related page ranges and keywords, the ground-truth image moved upward in the ranking. Nevertheless, Image Recall@1 remained at 44.3%, and neither statistical significance nor generalization to external data was evaluated. G4 should therefore be interpreted as an internal pilot method for adjusting a candidate ranking rather than as a method that reliably selects a single correct image.

G4 incorporates page- and section-level context, but it could not reliably distinguish multiple images on the same page or similar configuration screens within the same section. Because BBox is a preprocessing candidate gate, it does not directly discriminate among similar images that pass the filter. Local text around each BBox, image-level captions, image-order information, and more fine-grained training-stage classification are possible directions for improving image-level discrimination.

In the response-quality evaluation, G4-Qwen achieved a mean score of 3.99, which was higher than the other two models under G4 but lower than Qwen under G2 and G3. This result provides limited evidence that a quantized 7B-class local model can generate training guidance, but improvements in retrieval metrics did not consistently translate into better generated responses. The contribution of G4 is therefore centered on evidence retrieval and image-candidate ranking rather than generation quality.

## 8. Conclusion

This study proposed a context-aware multimodal RAG framework for collaborative robot training and evaluated retrieval performance using 70 queries derived from a collaborative robot training manual. Text-only RAG achieved high Recall@k for manual-text retrieval, and G3 combined the text results with image and diagram retrieval signals.

G4 estimated the training stage from the query and re-ranked G3 candidates using a stage-specific context map. Image Recall@5 increased from 74.3% to 85.7%, Image Recall@10 increased from 84.3% to 92.9%, and Image MRR increased from 0.534 to 0.608. However, Image Recall@1 remained below 50% at 44.3%, and weight selection and final evaluation used the same dataset. The results should therefore be interpreted as an improvement in relevant image-candidate ranking on the internal pilot dataset rather than as a resolution of the image-retrieval problem.

The results demonstrate the applicability of stage-context-aware multimodal re-ranking to collaborative robot training manuals that jointly use text, images, diagrams, and procedural information. However, response quality did not improve consistently, and the framework was not evaluated on independent data or on an actual system with approximately 8 GB of RAM. Accordingly, the present contribution is limited to retrieval-stage improvements under the reported experimental setting. Subsequent work will examine fine-grained image discrimination and prompt and evidence composition, followed by validation on separate data and evaluation with learners or domain experts before claims concerning educational effectiveness are made.

## References

[1] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in Advances in Neural Information Processing Systems, 2020. https://arxiv.org/abs/2005.11401

[2] V. Karpukhin et al., "Dense Passage Retrieval for Open-Domain Question Answering," in Proc. EMNLP, 2020. https://aclanthology.org/2020.emnlp-main.550/

[3] S. Robertson and H. Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond," Foundations and Trends in Information Retrieval, 2009. https://doi.org/10.1561/1500000019

[4] J. Chen et al., "BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation," in Findings of ACL, 2024. https://arxiv.org/abs/2402.03216

[5] A. Radford et al., "Learning Transferable Visual Models From Natural Language Supervision," in Proc. ICML, 2021. https://arxiv.org/abs/2103.00020

[6] X. Zhai et al., "Sigmoid Loss for Language Image Pre-Training," arXiv:2303.15343, 2023. https://arxiv.org/abs/2303.15343

[7] Qwen Team, "Qwen2.5 Technical Report," arXiv:2412.15115, 2024. https://arxiv.org/abs/2412.15115

[8] Gemma Team, "Gemma 2: Improving Open Language Models at a Practical Size," arXiv:2408.00118, 2024. https://arxiv.org/abs/2408.00118

[9] Meta AI, "The Llama 3 Herd of Models," arXiv:2407.21783, 2024. https://arxiv.org/abs/2407.21783

[10] T. Dettmers et al., "QLoRA: Efficient Finetuning of Quantized LLMs," in Advances in Neural Information Processing Systems, 2023. https://arxiv.org/abs/2305.14314

[11] Chroma, "Chroma Docs: Introduction." https://docs.trychroma.com/docs/overview/introduction

[12] A. Djuric, J. L. Rickli, V. M. Jovanovic, and D. Foster, "Hands-On Learning Environment and Educational Curriculum on Collaborative Robotics," in Proc. ASEE Annual Conference, 2017. https://digitalcommons.odu.edu/engtech_fac_pubs/78/

[13] Doosan Robotics, "User Manual / DART-Platform Manual." https://manual.doosanrobotics.com/en/user-manual/3.6.0/1-m-h-series/part-6-dart-platform-manual
