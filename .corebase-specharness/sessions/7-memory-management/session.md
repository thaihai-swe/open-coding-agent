---
{
  "feature": "7-memory-management",
  "phase": "Spec",
  "skill": "spec-requirements",
  "created_by": "corebase-specharness",
  "started_at": "2026-08-23T22:38:26",
  "last_context_fingerprint": {
    "corebase-specharness/memories/repo/core-policies.md": "7b08bd7edc6d7afd04b66a1c93b64d2a29ef027ddb2c7c6039d78930c1152cea",
    "corebase-specharness/rules/caveman.md": "6c7d369602ec2ab048cc85475faa7a7637b497ebf9515e97610eed2870f7b08f",
    "corebase-specharness/project/project-constraints.md": "6dd3aaaabe7e87b4d6c575519264ce2e8791008551c9fd9149e858af10da6696",
    "corebase-specharness/project/product-sense.md": "58003928c3b0f937452778708989c0736984f733d5ee79ea92b5bd8b7e23e539",
    "artifacts/features/7-memory-management/status.md": "df8b4ad851cfe66e1842f0ca439eb36d9ed8cdd5d5796e75321f6098c98babb6",
    "documents/BUILDING_A_CODING_AGENT.md": "6c5722aa37494b89b119323241c45c22d92d858aa85a3650887dc95763d80774",
    "AGENTS.md": "cdf440c3c9be23c88f1a2d6ab136b51773d3f6aaf3538ba5927cf85151f26ef5",
    "manifest.json": "ae1719a0d23ff6758df8b9d3deee5eef3fd5f3a59333eca047f17af7163ee59b",
    "src/tools/skills.py": "0d2dc3c80f0806cf2c411e7f0fa7e083ca5d2a5200cddd8cadeae77fef9bf2c1",
    "src/tools/task_board.py": "60420e15f910913395ddf5f951a01d32b4b95cc949f25748660f940e946b18ca",
    "src/tools/prompt.py": "2c4f2cce9aa7075b94bf7c6d88ee69355155d1e9b8ea2b759feb06463347bfed",
    "artifacts/features/7-memory-management/spec.md": "0419e448635c286db6886cf74c8b2f5a6d676a382b1c245e072f1d5d80c8c7dc",
    ".corebase-specharness/sessions/7-memory-management/session.md": "426b5d45d335250e2d1e7074109776b8796eba7b7c4fe277a967daf4e5f5a129",
    "corebase-specharness/rules/ponytail.md": "4efd234dc1d638b845efff6c4ba51c75ea565c10c7b86bfcd2bd113d0c732206",
    "corebase-specharness/project/architecture.md": "108425de27dba0d22d3d07f0588e2da5ee5072a589814f043f111f1f1eecc9f9",
    "artifacts/features/7-memory-management/plan.md": "2b944692eaa0242b523a3a94c329d9db4cb0cb8291b4573202eaeb5599dca4fe",
    "corebase-specharness/rules/code-design.md": "a1561dea5d1865986ea8f256a7758a209f0df969d43b8ab786ba77518b4ee35b",
    "src/prompts/planning.md": "d5f978a2f7902cfe8825c28f6f91a5684afc0f3c91ef3ed57d0f565637ab905a",
    "src/application/query_engine.py": "9f0be82e625ccd6f1404b42264b8f4f4eb3608101f3213e3f3cb0a6324ce3615",
    "src/tools/handlers/search.py": "79f46a98cb832c5fecd77b54fad2609fccf5d6c1c49f358f85811582350dc960",
    "artifacts/features/7-memory-management/tasks.md": "a1e681141ef7761b7492e3e852ebd1976106d3abb4d0901d50504f8243cb9fcf",
    "corebase-specharness/rules/security.md": "6d45506ccb7025e367df250a8f9038ad02ab6c8f4527a4bbdefa25c7da9ccf6c",
    "tests/query_engine_check.py": "49c9256d29a72af16186495c9a4a6223a6b70e827faa881627cfb8dd026319b1",
    "src/prompts/compact.md": "86f2a319c2a58e8634e2ccd560a9fc1aabdc4c5ef64a26d98ac8bc9dcfbee40c",
    "src/prompts/memory.md": "dbcd0d515a40c1afe4ac3b604ae0325243ba5ae96bb76dfbf3c9b92449135416",
    "src/prompts/security.md": "7c6c32c1a36d76190f49e8a90a02f3538b007cb659025b4653382810165f2985",
    "documents/how-to-run.md": "0e04a0b4c5026c53fad45eacf8e5700a70f06fc8edea56883c778fb390dd2cc3"
  },
  "last_context_slices": {
    "corebase-specharness/memories/repo/core-policies.md": {
      "Purpose": "593fcff71805a615aea22031949c3e8d675ded3f3a4176eb827bd291728ae302",
      "Normative Rules": "5de2d3e922ba3eaf27dfdc23646b7052bc4ae0ab56c7e112561dedfd3f93e046",
      "Security Policy": "d8ff6e79643f18bc999364379a34a77726e67a05e067aaff769ff2cb67a3b515"
    },
    "corebase-specharness/rules/caveman.md": {
      "": "6c7d369602ec2ab048cc85475faa7a7637b497ebf9515e97610eed2870f7b08f"
    },
    "corebase-specharness/project/project-constraints.md": {
      "Performance Budgets": "fe53dc74f9f237205735033011a02fa3b6098687a712722223a25cbb2b34b730",
      "Compliance Requirements": "f73ef1e241ef796e497e445bb9cff6ce0b3e1f62a4337bf5684d4625cc5f714f",
      "Security Requirements": "0879cfc8bac162b34144fb5a0c5cd22dd7614cfef685434a3f0665e9e49ff057",
      "Operational Constraints": "7e77c42d3622cd179a94829c367fdd7eb7cd32fb5edbe5af69b026f179412179"
    },
    "corebase-specharness/project/product-sense.md": {
      "Product Vision": "30f99f5abd3d1a371b773afbbfaa2329ababa1f959673e773d799f21523385b4",
      "Problem Statement": "b7cdd788535c101dceeab1b13f60a26b5a3972a747a7543c5ece4b1f06e00f1f",
      "Domain Context & Business Rules": "943c36b452c8cc9dafb9d093180f2cb6a0235244095920c45649b4c11d3241a1",
      "Success Metrics": "b16dc89f033d946ce46df92af941c6b7401eb8460a675382edff1c83896467cd"
    },
    "artifacts/features/7-memory-management/status.md": {
      "": "f8025a1423fce6bfed8f4c084efe8f78af15d343ca2fd7f89d0d9e96662eddc5",
      "Intake": "ebe181b3ae261c3ce4feee21a9eab1ee847dbfb3185b48310e099f1c4d9f69a0",
      "Blockers / Decisions": "539c9d8db2bbef5f812a3292f61e55ddad6e3ee4c26b0297867cc87da3c4b926",
      "Facts (not decisions)": "5724eaabaea26a822af636f10d8719f328f56b629e10031bc962785fb8a06dd3"
    },
    "documents/BUILDING_A_CODING_AGENT.md": {
      "": "6c5722aa37494b89b119323241c45c22d92d858aa85a3650887dc95763d80774"
    },
    "AGENTS.md": {
      "": "cdf440c3c9be23c88f1a2d6ab136b51773d3f6aaf3538ba5927cf85151f26ef5"
    },
    "manifest.json": {
      "": "ae1719a0d23ff6758df8b9d3deee5eef3fd5f3a59333eca047f17af7163ee59b"
    },
    "src/tools/skills.py": {
      "": "0d2dc3c80f0806cf2c411e7f0fa7e083ca5d2a5200cddd8cadeae77fef9bf2c1"
    },
    "src/tools/task_board.py": {
      "": "60420e15f910913395ddf5f951a01d32b4b95cc949f25748660f940e946b18ca"
    },
    "src/tools/prompt.py": {
      "": "2c4f2cce9aa7075b94bf7c6d88ee69355155d1e9b8ea2b759feb06463347bfed"
    },
    "artifacts/features/7-memory-management/spec.md": {
      "Outcome": "950cdd0f8528369f40bce0c0740e495f825559cb9aea206d6f15854f74557042",
      "Requirements (Moderate/Complex)": "8d73d37055c1e38c23288e0912d441d5194d6cb92008293ba2c332dcfb4d3b5e",
      "Metadata": "b647f27bbeca42b1c0c43d175e7dc957c8c67c2566454f35c46bfb56560c4181",
      "Problem Statement": "2423b92518feca753704907952d833beb9b55c764c4c896df9aa044e3cc02b93",
      "Acceptance Criteria": "4a3e849b003409aceaabec34207011198a3a5dea3a2bd2cc5754c82108e2f120",
      "": "69ac7b6643a185bdda193f3302a4c0212370fd7a82a1546af90a12fa4fbd3d0c",
      "Scope": "2e7c4bcf6bd53a866eeb280a7e64b3cf5bc51d13603b139b6f3dcfde9099ecf8",
      "User Stories & Journeys (Moderate/Complex)": "0ec113e01430ad93dcd9f0b6b8ed22c990b4a7d822f6e1ba217cfaab87180ea8",
      "Constraints and Risk": "4742065f875742d828e46267dc1cfc66f5d9637433fc609496dd5615d0f83ab8"
    },
    ".corebase-specharness/sessions/7-memory-management/session.md": {
      "": "426b5d45d335250e2d1e7074109776b8796eba7b7c4fe277a967daf4e5f5a129"
    },
    "corebase-specharness/rules/ponytail.md": {
      "Decision Matrix: Should You Create an Abstraction?": "4efd234dc1d638b845efff6c4ba51c75ea565c10c7b86bfcd2bd113d0c732206"
    },
    "corebase-specharness/project/architecture.md": {
      "System Snapshot": "f596ccc1d514abed0ce88e00c11a79c6599181cbb4980afcc227b904ee8459c3",
      "Top-Level Components": "c297468cfc0e40b612fdee03b09de284de833cd48c96f18356c0f8f00b5442e7",
      "Runtime Boundaries": "e2cc4449cfa7c6b7bc96fcd3222e9eb95e76569ee172afcd07b6423e427c7788",
      "Safe Change Guidance": "11d8495830bb43019627609d0c49cfcb296c513296fdfc6cce6cbb33820a05c8"
    },
    "artifacts/features/7-memory-management/plan.md": {
      "Delivery": "f4855cdc919d72057e8abf07535e5970941874655af64c7e36d8e5bfd599f643",
      "Metadata": "65bf0250511ac497df622babac62186a6e886c3c5ffa242d843e8d42c0cf302a",
      "Lightweight Design": "0a7086a1f32c3ecefd044a89387cf537f0423cfc2e4f1b8b4eeda7a35e4a805c",
      "": "5c18db04ff0918817e9cce3bc112da7be8de8602dcec443fca1fe6f1332993b9"
    },
    "corebase-specharness/rules/code-design.md": {
      "Read before you write": "b87c8381ed324fdbeb44fe268d2fca86b6d303bc22be907a245253932403587e",
      "Abstraction Check & Deep Modules": "aaa9d0721906c50d4844cc94675b4dd9aa94606e10e51902ba9e30b787d3ba11",
      "Clean Architecture & Layering": "60c38fee244c9ed1f416c640d3ab3ee21d6fc60575662b595b09feda795de551",
      "Failures must reach a decision-maker": "e10a8fb4ec54fd672443f0e13ef53e081078b2b14a27aa7f304d81e1de5f6dc8",
      "Verify the path you claim to have fixed": "11d21e9b3e8f7a90e8b9e9328111be65582cd0a8bea5aa8cc5896eaf990f72ba"
    },
    "src/prompts/planning.md": {
      "": "d5f978a2f7902cfe8825c28f6f91a5684afc0f3c91ef3ed57d0f565637ab905a"
    },
    "src/application/query_engine.py": {
      "": "9f0be82e625ccd6f1404b42264b8f4f4eb3608101f3213e3f3cb0a6324ce3615"
    },
    "src/tools/handlers/search.py": {
      "": "79f46a98cb832c5fecd77b54fad2609fccf5d6c1c49f358f85811582350dc960"
    },
    "artifacts/features/7-memory-management/tasks.md": {
      "Tasks": "d1a8fa51534fa6195b25f50f282ee7976ba838462720cfb20f66b26c21efec9b",
      "Metadata": "9509b3f18380632ce752e751a1b729441fb2c2acf74febdebbc045a71e3e33bd",
      "": "a1e681141ef7761b7492e3e852ebd1976106d3abb4d0901d50504f8243cb9fcf"
    },
    "corebase-specharness/rules/security.md": {
      "Core Rules": "b6dcc21cfaffcf9524f98d35de7eb85d95cc9090034b5b215b8c82a36087a684",
      "Shell and Script Safety": "e5b81bd9723d6b4c594434a13bea59e7dba651eca52431f5ebcd5894e1573c2f",
      "File and Artifact Boundaries": "3e5aef08454dd138b7b469e1491d15d5ac06992f39f3f76174ff83b40e82aab4",
      "Verification": "30a680fde0bb2ebbf070856e6e8422f850f4ac281ecc9163846972d6be5ae415"
    },
    "tests/query_engine_check.py": {
      "": "49c9256d29a72af16186495c9a4a6223a6b70e827faa881627cfb8dd026319b1"
    },
    "src/prompts/compact.md": {
      "": "86f2a319c2a58e8634e2ccd560a9fc1aabdc4c5ef64a26d98ac8bc9dcfbee40c"
    },
    "src/prompts/memory.md": {
      "": "dbcd0d515a40c1afe4ac3b604ae0325243ba5ae96bb76dfbf3c9b92449135416"
    },
    "src/prompts/security.md": {
      "": "7c6c32c1a36d76190f49e8a90a02f3538b007cb659025b4653382810165f2985"
    },
    "documents/how-to-run.md": {
      "": "0e04a0b4c5026c53fad45eacf8e5700a70f06fc8edea56883c778fb390dd2cc3"
    }
  },
  "token_usage_estimate": 27425,
  "last_context_tokens": 1286,
  "updates": 5
}
---
# Session

## Objective

Define requirements for Feature 7-memory-management based on s09 and BUILDING_A_CODING_AGENT.md

## Progress

[not started]

## Handoff

[not prepared]

## Progress Update

exited spec-requirements

## Handoff Update

- Next step: /spec-plan

## Progress Update

exited spec-requirements

## Handoff Update

- Next step: /spec-plan

## Progress Update

exited spec-plan

## Handoff Update

- Next step: /spec-tasks

## Progress Update

exited spec-tasks

## Handoff Update

- Next step: /spec-implement

## Progress Update

exited spec-implement

## Handoff Update

- Next step: /harness-verify
