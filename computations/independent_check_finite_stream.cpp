#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include <zlib.h>

using u8 = std::uint8_t;
using u16 = std::uint16_t;
using u32 = std::uint32_t;
using u64 = std::uint64_t;
using u128 = unsigned __int128;

constexpr int kBaseIndex = 4000;
constexpr int kBaseN = 100006;
constexpr int kCompactEndIndex = 4000000;

// Base stream schema inferred from the submitted decoder and independently
// enforced here: after gzip decompression, bytes are
//   8-byte magic E848D1\0\0; uint32_le endpoint_count (=4000);
//   for endpoint i=1..4000: uint32_le update_count, followed by that many
//   (uint32_le vertex, uint16_le colour) records.
// Delta state persists between endpoints.  Exact EOF is required.
// Compact stream schema: 8-byte magic E848C3\0\0; uint32_le base_index,
// end_index, step_count; then per step uint32_le swap_code, uint8 placement
// count, and that many (uint32_le outsider, uint32_le target_bin) records.
// The output factor-leaf stream is 8-byte magic E848L1\0\0, a uint64_le
// distinct-leaf count, the strictly increasing uint64_le leaves, and EOF.

int endpoint(int index) { return 25 * index + 6; }

u64 mulmod(u64 a, u64 b, u64 modulus) {
  return static_cast<u64>((static_cast<u128>(a) * b) % modulus);
}

u64 powmod(u64 base, u64 exponent, u64 modulus) {
  u64 result = 1;
  while (exponent != 0) {
    if (exponent & 1U) result = mulmod(result, base, modulus);
    base = mulmod(base, base, modulus);
    exponent >>= 1U;
  }
  return result;
}

std::vector<int> prime_sieve(int limit) {
  std::vector<u8> flag(static_cast<std::size_t>(limit) + 1, 1);
  flag[0] = flag[1] = 0;
  for (int p = 2; static_cast<std::int64_t>(p) * p <= limit; ++p) {
    if (!flag[static_cast<std::size_t>(p)]) continue;
    for (std::int64_t m = static_cast<std::int64_t>(p) * p;
         m <= limit; m += p) {
      flag[static_cast<std::size_t>(m)] = 0;
    }
  }
  std::vector<int> result;
  for (int p = 2; p <= limit; ++p) {
    if (flag[static_cast<std::size_t>(p)]) result.push_back(p);
  }
  return result;
}

// Generic Tonelli--Shanks, deliberately distinct from the submitted
// nonresidue^((p-1)/4) root constructor.
u64 tonelli_shanks(u64 n, u64 p) {
  if (p == 2) return n & 1U;
  n %= p;
  if (powmod(n, (p - 1) / 2, p) != 1) {
    throw std::runtime_error("Tonelli input is not a quadratic residue");
  }
  u64 q = p - 1;
  unsigned s = 0;
  while ((q & 1U) == 0) {
    q >>= 1U;
    ++s;
  }
  if (s == 1) return powmod(n, (p + 1) / 4, p);
  u64 z = 2;
  while (powmod(z, (p - 1) / 2, p) != p - 1) ++z;
  u64 c = powmod(z, q, p);
  u64 x = powmod(n, (q + 1) / 2, p);
  u64 t = powmod(n, q, p);
  unsigned m = s;
  while (t != 1) {
    unsigned i = 1;
    u64 probe = mulmod(t, t, p);
    while (probe != 1) {
      probe = mulmod(probe, probe, p);
      ++i;
      if (i >= m) throw std::runtime_error("Tonelli iteration failed");
    }
    const u64 b = powmod(c, u64{1} << (m - i - 1), p);
    x = mulmod(x, b, p);
    const u64 b2 = mulmod(b, b, p);
    t = mulmod(t, b2, p);
    c = b2;
    m = i;
  }
  return x;
}

std::vector<u8> independent_diagonal_sieve(
    int upper, const std::vector<int>& primes) {
  std::vector<u8> diagonal(static_cast<std::size_t>(upper) + 1, 0);
  for (int raw : primes) {
    if (raw < 5 || raw % 4 != 1) continue;
    const u64 p = static_cast<u64>(raw);
    const u64 r = tonelli_shanks(p - 1, p);
    const u64 quotient = (r * r + 1) / p;
    const u64 derivative_inverse = powmod((2 * r) % p, p - 2, p);
    const u64 correction = mulmod((p - quotient % p) % p,
                                  derivative_inverse, p);
    const u64 modulus = p * p;
    const u64 root = r + correction * p;
    if ((mulmod(root, root, modulus) + 1) % modulus != 0) {
      throw std::runtime_error("independent Hensel lift failed");
    }
    for (u64 residue : {root, modulus - root}) {
      for (u64 value = residue; value <= static_cast<u64>(upper);) {
        diagonal[static_cast<std::size_t>(value)] = 1;
        if (modulus > static_cast<u64>(upper) - value) break;
        value += modulus;
      }
    }
  }
  return diagonal;
}

class GzipInput {
 public:
  explicit GzipInput(const std::string& path) : file_(gzopen(path.c_str(), "rb")) {
    if (file_ == nullptr) throw std::runtime_error("cannot open " + path);
  }
  ~GzipInput() { if (file_ != nullptr) gzclose(file_); }
  void read(void* output, std::size_t size) {
    auto* cursor = static_cast<u8*>(output);
    while (size != 0) {
      const unsigned chunk = static_cast<unsigned>(std::min<std::size_t>(
          size, std::numeric_limits<unsigned>::max()));
      const int got = gzread(file_, cursor, chunk);
      if (got <= 0) throw std::runtime_error("truncated gzip input");
      cursor += got;
      size -= static_cast<std::size_t>(got);
    }
  }
  bool trailing() {
    u8 value = 0;
    const int got = gzread(file_, &value, 1);
    if (got < 0) throw std::runtime_error("gzip read error");
    return got != 0;
  }
 private:
  gzFile file_;
};

u8 read8(GzipInput& input) {
  u8 value = 0;
  input.read(&value, 1);
  return value;
}
u16 read16(GzipInput& input) {
  std::array<u8, 2> b{};
  input.read(b.data(), b.size());
  return static_cast<u16>(static_cast<u16>(b[0]) |
                          (static_cast<u16>(b[1]) << 8));
}
u32 read32(GzipInput& input) {
  std::array<u8, 4> b{};
  input.read(b.data(), b.size());
  return static_cast<u32>(b[0]) | (static_cast<u32>(b[1]) << 8) |
         (static_cast<u32>(b[2]) << 16) | (static_cast<u32>(b[3]) << 24);
}

struct PairOracle {
  const std::vector<int>& primes;
  std::vector<u64> cache_keys;
  std::vector<u8> cache_states;
  std::size_t cache_mask = 0;
  std::size_t queries = 0;
  std::size_t computations = 0;
  std::size_t hits = 0;
  std::size_t overwrites = 0;
  mutable std::vector<u64> accepted_factor_leaves;

  explicit PairOracle(const std::vector<int>& all_primes)
      : primes(all_primes) {
    constexpr std::size_t capacity = std::size_t{1} << 23;
    cache_keys.assign(capacity, 0);
    cache_states.assign(capacity, 0);
    cache_mask = capacity - 1;
  }

  static u64 mix(u64 value) {
    value ^= value >> 30U;
    value *= 0xbf58476d1ce4e5b9ULL;
    value ^= value >> 27U;
    value *= 0x94d049bb133111ebULL;
    return value ^ (value >> 31U);
  }

  static u64 difference(u64 a, u64 b) {
    return a > b ? a - b : b - a;
  }

  // This probable-prime predicate is only a factorization accelerator.  Every
  // terminal leaf in every accepted proof obligation is emitted and must pass
  // the separate exact sieve/primorial-gcd certificate before this verifier's
  // positive result is usable.
  static bool probable_prime64(u64 n) {
    if (n < 2) return false;
    for (u64 p : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL,
                  19ULL, 23ULL, 29ULL, 31ULL, 37ULL}) {
      if (n % p == 0) return n == p;
    }
    u64 odd = n - 1;
    unsigned twos = 0;
    while ((odd & 1U) == 0) {
      odd >>= 1U;
      ++twos;
    }
    constexpr std::array<u64, 7> witnesses{
        2ULL, 325ULL, 9375ULL, 28178ULL,
        450775ULL, 9780504ULL, 1795265022ULL};
    for (u64 witness : witnesses) {
      if (witness % n == 0) continue;
      u64 x = powmod(witness % n, odd, n);
      if (x == 1 || x == n - 1) continue;
      bool passed = false;
      for (unsigned round = 1; round < twos; ++round) {
        x = mulmod(x, x, n);
        if (x == n - 1) {
          passed = true;
          break;
        }
      }
      if (!passed) return false;
    }
    return true;
  }

  // Clean-room deterministic Brent rho.  Failure throws; it never converts
  // an incomplete factorization into a squarefree result.
  static u64 split_composite(u64 n) {
    if (n % 2 == 0) return 2;
    if (n % 3 == 0) return 3;
    constexpr u64 batch = 64;
    for (u64 attempt = 1; attempt <= 4096; ++attempt) {
      const u64 constant = 2 * attempt + 1;
      auto step = [n, constant](u64 x) {
        return (mulmod(x, x, n) + constant) % n;
      };
      u64 y = 2 + attempt % (n - 3);
      u64 radius = 1;
      u64 divisor = 1;
      u64 x = 0;
      u64 saved = y;
      while (divisor == 1 && radius <= (u64{1} << 22)) {
        x = y;
        for (u64 j = 0; j < radius; ++j) y = step(y);
        for (u64 consumed = 0; consumed < radius && divisor == 1;) {
          saved = y;
          const u64 count = std::min(batch, radius - consumed);
          u64 product = 1;
          for (u64 j = 0; j < count; ++j) {
            y = step(y);
            product = mulmod(product, difference(x, y), n);
          }
          divisor = std::gcd(product, n);
          consumed += count;
        }
        radius <<= 1U;
      }
      if (divisor == n) {
        do {
          saved = step(saved);
          divisor = std::gcd(difference(x, saved), n);
        } while (divisor == 1);
      }
      if (divisor > 1 && divisor < n) return divisor;
    }
    throw std::runtime_error("independent factor splitter exhausted retries");
  }

  static void factor_recursive(u64 value, std::vector<u64>& factors) {
    if (value == 1) return;
    if (probable_prime64(value)) {
      factors.push_back(value);
      return;
    }
    const u64 divisor = split_composite(value);
    factor_recursive(divisor, factors);
    factor_recursive(value / divisor, factors);
  }

  bool compute_direct(u64 value) const {
    for (int raw : primes) {
      const u64 p = static_cast<u64>(raw);
      const u64 square = p * p;
      if (square > value) break;
      if (value % square == 0) return false;
    }
    return true;
  }

  bool compute_factored(u64 value) const {
    const u64 original = value;
    std::vector<u64> factors;
    for (int raw : primes) {
      if (raw > 1000) break;
      const u64 p = static_cast<u64>(raw);
      while (value % p == 0) {
        factors.push_back(p);
        value /= p;
        if (factors.size() >= 2 &&
            factors[factors.size() - 2] == factors.back()) {
          return false;
        }
      }
    }
    factor_recursive(value, factors);
    std::sort(factors.begin(), factors.end());
    if (std::adjacent_find(factors.begin(), factors.end()) != factors.end()) {
      return false;
    }
    u128 product = 1;
    for (u64 factor : factors) product *= factor;
    if (product != static_cast<u128>(original)) {
      throw std::runtime_error("independent factorization is incomplete");
    }
    accepted_factor_leaves.insert(
        accepted_factor_leaves.end(), factors.begin(), factors.end());
    return true;
  }

  bool squarefree(u64 value) {
    if (value < 2) throw std::runtime_error("invalid pair value");
    ++queries;
    const std::size_t slot = static_cast<std::size_t>(mix(value)) & cache_mask;
    if (cache_states[slot] != 0 && cache_keys[slot] == value) {
      ++hits;
      return cache_states[slot] == 1;
    }
    if (cache_states[slot] != 0) ++overwrites;
    ++computations;
    const bool answer = compute_factored(value);
    cache_keys[slot] = value;
    cache_states[slot] = answer ? 1 : 2;
    return answer;
  }
  bool compatible(u32 a, u32 b) {
    return squarefree(static_cast<u64>(a) * b + 1);
  }
};

struct BaseState {
  std::vector<u32> anchor18;
  std::vector<u32> outsider;
};

BaseState check_base(
    const std::string& path,
    const std::vector<u8>& diagonal,
    PairOracle& oracle) {
  GzipInput input(path);
  std::array<char, 8> magic{};
  input.read(magic.data(), magic.size());
  const std::array<char, 8> expected{'E','8','4','8','D','1','\0','\0'};
  if (magic != expected || read32(input) != kBaseIndex) {
    throw std::runtime_error("bad base header");
  }
  std::vector<int> colour(static_cast<std::size_t>(kBaseN) + 1, -1);
  std::size_t changes_total = 0;
  std::size_t endpoint_pairs = 0;
  std::vector<u32> diagonal_vertices;
  for (u32 vertex = 1; vertex <= static_cast<u32>(kBaseN); ++vertex) {
    if (diagonal[static_cast<std::size_t>(vertex)]) {
      diagonal_vertices.push_back(vertex);
    }
  }
  std::size_t diagonal_count = 0;
  for (int index = 1; index <= kBaseIndex; ++index) {
    const int n = endpoint(index);
    const u32 changes = read32(input);
    changes_total += changes;
    for (u32 j = 0; j < changes; ++j) {
      const u32 vertex = read32(input);
      const u16 c = read16(input);
      if (vertex == 0 || vertex > static_cast<u32>(n) || c >= index ||
          !diagonal[static_cast<std::size_t>(vertex)]) {
        throw std::runtime_error("invalid base update");
      }
      colour[static_cast<std::size_t>(vertex)] = c;
    }
    while (diagonal_count < diagonal_vertices.size() &&
           diagonal_vertices[diagonal_count] <= static_cast<u32>(n)) {
      ++diagonal_count;
    }
    {
      std::vector<std::vector<u32>> classes(static_cast<std::size_t>(index));
      for (std::size_t j = 0; j < diagonal_count; ++j) {
        const u32 vertex = diagonal_vertices[j];
        const int c = colour[static_cast<std::size_t>(vertex)];
        if (c < 0 || c >= index) {
          throw std::runtime_error("endpoint diagonal vertex uncoloured");
        }
        classes[static_cast<std::size_t>(c)].push_back(
            vertex);
      }
      for (int c = 0; c < index; ++c) {
        const auto& members = classes[static_cast<std::size_t>(c)];
        const u32 anchor = static_cast<u32>(7 + 25 * c);
        if (std::find(members.begin(), members.end(), anchor) == members.end()) {
          throw std::runtime_error("prefix class lacks canonical anchor");
        }
        for (std::size_t a = 0; a < members.size(); ++a) {
          for (std::size_t b = 0; b < a; ++b) {
            ++endpoint_pairs;
            if (!oracle.compatible(members[a], members[b])) {
              throw std::runtime_error("endpoint pair is nonsquarefree");
            }
          }
        }
      }
    }
  }
  if (input.trailing()) throw std::runtime_error("base trailing data");
  if (endpoint_pairs != 18049789) {
    throw std::runtime_error("base endpoint pair count mismatch");
  }

  std::vector<std::vector<u32>> classes(kBaseIndex);
  int exact_diagonal_count = 0;
  for (int vertex = 1; vertex <= kBaseN; ++vertex) {
    const bool is_diagonal = diagonal[static_cast<std::size_t>(vertex)] != 0;
    const bool is_coloured = colour[static_cast<std::size_t>(vertex)] >= 0;
    if (is_diagonal != is_coloured) {
      throw std::runtime_error("base final coloured set differs from diagonal set");
    }
    if (is_diagonal) {
      ++exact_diagonal_count;
      classes[static_cast<std::size_t>(colour[static_cast<std::size_t>(vertex)])]
          .push_back(static_cast<u32>(vertex));
    }
  }
  if (exact_diagonal_count != 10511) {
    throw std::runtime_error("unexpected independent base diagonal count");
  }
  BaseState result;
  result.anchor18.resize(kBaseIndex);
  result.outsider.resize(kBaseIndex);
  std::vector<u8> seen18(kBaseIndex, 0);
  int outsider_count = 0;
  std::size_t top_pairs = 0;
  for (int c = 0; c < kBaseIndex; ++c) {
    int roots7 = 0;
    int roots18 = 0;
    int outsiders = 0;
    for (u32 v : classes[static_cast<std::size_t>(c)]) {
      if (v % 25 == 7) {
        ++roots7;
        if (v != static_cast<u32>(7 + 25 * c)) {
          throw std::runtime_error("base canonical 7 anchor moved");
        }
      } else if (v % 25 == 18) {
        ++roots18;
        result.anchor18[static_cast<std::size_t>(c)] = v;
      } else {
        ++outsiders;
        result.outsider[static_cast<std::size_t>(c)] = v;
        ++outsider_count;
      }
    }
    if (roots7 != 1 || roots18 != 1 || outsiders > 1) {
      throw std::runtime_error("base top bin shape failed");
    }
    const auto& members = classes[static_cast<std::size_t>(c)];
    for (std::size_t a = 0; a < members.size(); ++a) {
      for (std::size_t b = 0; b < a; ++b) {
        ++top_pairs;
        if (!oracle.compatible(members[a], members[b])) {
          throw std::runtime_error("base top pair is nonsquarefree");
        }
      }
    }
    const u32 a18 = result.anchor18[static_cast<std::size_t>(c)];
    if (a18 < 18 || (a18 - 18) % 25 != 0) {
      throw std::runtime_error("bad base 18 anchor");
    }
    const u32 rank = (a18 - 18) / 25;
    if (rank >= static_cast<u32>(kBaseIndex) || seen18[rank]) {
      throw std::runtime_error("base 18 anchors are not a permutation");
    }
    seen18[rank] = 1;
  }
  if (outsider_count != 2511) {
    throw std::runtime_error("unexpected base outsider count");
  }
  std::cout << "independent_base_changes=" << changes_total << "\n";
  std::cout << "independent_base_endpoint_pairs=" << endpoint_pairs
            << " endpoint_count=" << kBaseIndex << "\n";
  std::cout << "independent_base_top_pairs=" << top_pairs << "\n";
  return result;
}

void check_bin_pairs(
    u32 index,
    const std::vector<u32>& anchor18,
    const std::vector<u32>& outsider,
    PairOracle& oracle,
    std::size_t& pair_count) {
  const u32 a7 = 7 + 25 * index;
  const u32 a18 = anchor18[static_cast<std::size_t>(index)];
  ++pair_count;
  if (!oracle.compatible(a7, a18)) {
    throw std::runtime_error("compact anchor pair is nonsquarefree");
  }
  const u32 z = outsider[static_cast<std::size_t>(index)];
  if (z != 0) {
    pair_count += 2;
    if (!oracle.compatible(a7, z) || !oracle.compatible(a18, z)) {
      throw std::runtime_error("compact outsider pair is nonsquarefree");
    }
  }
}

void check_compact(
    const std::string& path,
    const std::vector<u8>& diagonal,
    BaseState state,
    PairOracle& oracle) {
  GzipInput input(path);
  std::array<char, 8> magic{};
  input.read(magic.data(), magic.size());
  const std::array<char, 8> expected{'E','8','4','8','C','3','\0','\0'};
  const u32 base = read32(input);
  const u32 end = read32(input);
  const u32 steps = read32(input);
  if (magic != expected || base != kBaseIndex || end != kCompactEndIndex ||
      steps != end - base) {
    throw std::runtime_error("bad compact header");
  }
  state.anchor18.reserve(kCompactEndIndex);
  state.outsider.reserve(kCompactEndIndex);
  std::size_t swaps = 0;
  std::size_t placements = 0;
  std::size_t sampled_pairs = 0;
  std::size_t all_pair_occurrences = 0;
  int previous_n = kBaseN;
  for (int index = kBaseIndex + 1; index <= kCompactEndIndex; ++index) {
    const int current_n = endpoint(index);
    const u32 new7 = static_cast<u32>(7 + 25 * (index - 1));
    const u32 new18 = new7 + 11;
    state.anchor18.push_back(new18);
    state.outsider.push_back(0);
    const u32 new_bin = static_cast<u32>(index - 1);
    std::vector<u32> affected{new_bin};
    const u32 swap_code = read32(input);
    if (swap_code != 0) {
      const u32 target = swap_code - 1;
      if (target >= new_bin) throw std::runtime_error("swap not in old bin");
      std::swap(state.anchor18[static_cast<std::size_t>(target)],
                state.anchor18[static_cast<std::size_t>(new_bin)]);
      affected.push_back(target);
      ++swaps;
    }
    if (!diagonal[static_cast<std::size_t>(new7)] ||
        !diagonal[static_cast<std::size_t>(new18)]) {
      throw std::runtime_error("principal compact anchor not diagonal");
    }
    std::vector<u32> expected_outsiders;
    for (int v = previous_n + 1; v <= current_n; ++v) {
      if (diagonal[static_cast<std::size_t>(v)] &&
          v != static_cast<int>(new7) && v != static_cast<int>(new18)) {
        expected_outsiders.push_back(static_cast<u32>(v));
      }
    }
    const u8 count = read8(input);
    std::vector<u32> named;
    named.reserve(count);
    for (u8 j = 0; j < count; ++j) {
      const u32 outsider = read32(input);
      const u32 target = read32(input);
      if (target >= static_cast<u32>(index) ||
          state.outsider[static_cast<std::size_t>(target)] != 0 ||
          outsider <= static_cast<u32>(previous_n) ||
          outsider > static_cast<u32>(current_n) ||
          outsider % 25 == 7 || outsider % 25 == 18) {
        throw std::runtime_error("invalid compact outsider placement");
      }
      state.outsider[static_cast<std::size_t>(target)] = outsider;
      affected.push_back(target);
      named.push_back(outsider);
      ++placements;
    }
    if (named != expected_outsiders) {
      throw std::runtime_error("compact outsider list is not exact");
    }
    std::sort(affected.begin(), affected.end());
    affected.erase(std::unique(affected.begin(), affected.end()), affected.end());
    for (u32 bin : affected) {
      all_pair_occurrences +=
          state.outsider[static_cast<std::size_t>(bin)] == 0 ? 1 : 3;
    }
    for (u32 bin : affected) {
      check_bin_pairs(bin, state.anchor18, state.outsider,
                      oracle, sampled_pairs);
    }
    previous_n = current_n;
  }
  if (input.trailing()) throw std::runtime_error("compact trailing data");
  if (placements != 2513387 || swaps != 1379312) {
    throw std::runtime_error("compact transition counters differ");
  }
  if (all_pair_occurrences != 14458371 ||
      sampled_pairs != all_pair_occurrences) {
    throw std::runtime_error("compact affected-pair count mismatch");
  }
  std::vector<u8> seen18(kCompactEndIndex, 0);
  for (int c = 0; c < kCompactEndIndex; ++c) {
    const u32 value = state.anchor18[static_cast<std::size_t>(c)];
    if (value < 18 || (value - 18) % 25 != 0) {
      throw std::runtime_error("final compact 18 anchor residue failed");
    }
    const u32 rank = (value - 18) / 25;
    if (rank >= static_cast<u32>(kCompactEndIndex) || seen18[rank]) {
      throw std::runtime_error("final compact 18 permutation failed");
    }
    seen18[rank] = 1;
  }
  std::cout << "independent_compact_steps=" << steps
            << " swaps=" << swaps << " placements=" << placements << "\n";
  std::cout << "independent_compact_pair_occurrences=" << all_pair_occurrences
            << " checked=" << sampled_pairs << "\n";
}

int main(int argc, char** argv) {
  try {
    if (argc != 4) {
      throw std::runtime_error(
          "usage: checker BASE_CERT COMPACT_CERT FACTOR_LEAVES");
    }
    const int upper = endpoint(kCompactEndIndex);
    std::cerr << "independent prime and Tonelli-Hensel sieve through "
              << upper << "\n";
    const std::vector<int> primes = prime_sieve(upper);
    const std::vector<u8> diagonal = independent_diagonal_sieve(upper, primes);
    const std::size_t diagonal_count = static_cast<std::size_t>(
        std::count(diagonal.begin(), diagonal.end(), 1));
    if (diagonal_count != 10515898) {
      throw std::runtime_error("independent full diagonal count mismatch");
    }
    for (int value = 1; value <= 6; ++value) {
      if (diagonal[static_cast<std::size_t>(value)]) {
        throw std::runtime_error("unexpected diagonal candidate below 7");
      }
    }
    PairOracle oracle(primes);
    for (const auto& [value, expected] : std::array<std::pair<u64, bool>, 8>{
             std::pair<u64, bool>{2, true},
             {50, false},
             {127, true},
             {775, false},
             {1'000'003ULL * 1'000'003ULL, false},
             {1'000'003ULL * 1'000'033ULL, true},
             {3'215'031'751ULL, true},
             {4'213'400'485ULL, false}}) {
      const bool observed = oracle.compute_factored(value);
      if (observed != expected || oracle.compute_direct(value) != expected) {
        throw std::runtime_error("independent factor-oracle self-test failed");
      }
    }
    for (u64 value = 2; value <= 20000; ++value) {
      if (oracle.compute_factored(value) != oracle.compute_direct(value)) {
        throw std::runtime_error(
            "independent factor-oracle exhaustive control failed");
      }
    }
    oracle.accepted_factor_leaves.clear();
    BaseState base = check_base(argv[1], diagonal, oracle);
    check_compact(argv[2], diagonal, std::move(base), oracle);
    auto& leaves = oracle.accepted_factor_leaves;
    std::sort(leaves.begin(), leaves.end());
    leaves.erase(std::unique(leaves.begin(), leaves.end()), leaves.end());
    std::ofstream output(argv[3], std::ios::binary | std::ios::trunc);
    if (!output) throw std::runtime_error("cannot create factor-leaf file");
    const std::array<char, 8> magic{'E','8','4','8','L','1','\0','\0'};
    output.write(magic.data(), static_cast<std::streamsize>(magic.size()));
    auto write64 = [&output](u64 value) {
      std::array<char, 8> bytes{};
      for (unsigned i = 0; i < 8; ++i) {
        bytes[i] = static_cast<char>((value >> (8U * i)) & 0xffU);
      }
      output.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
    };
    write64(static_cast<u64>(leaves.size()));
    for (u64 leaf : leaves) write64(leaf);
    output.close();
    if (!output) throw std::runtime_error("cannot write factor-leaf file");
    std::cout << "independent_factor_leaf_count=" << leaves.size() << "\n";
    std::cout << "independent_factor_leaf_max="
              << (leaves.empty() ? 0 : leaves.back()) << "\n";
    std::cout << "independent_total_diagonal=" << diagonal_count << "\n";
    std::cout << "independent_pair_computations=" << oracle.computations << "\n";
    std::cout << "independent_pair_queries_hits_overwrites=" << oracle.queries
              << "/" << oracle.hits << "/" << oracle.overwrites << "\n";
    std::cout << "independent_mode=full-with-factor-leaves\n";
    std::cout << "INDEPENDENT FINITE STREAM AUDIT PASSED\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "INDEPENDENT AUDIT FAILED: " << error.what() << "\n";
    return 1;
  }
}
