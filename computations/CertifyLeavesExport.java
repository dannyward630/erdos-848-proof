import java.io.BufferedInputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Exact batch primality certification for an E848L1 factor-leaf stream. */
public final class CertifyLeavesExport {
  private static final int CHUNK = 4096;
  private static final long PAIR_BOUND = 100_000_006L * 100_000_006L + 1L;

  private static long readLittleLong(InputStream input) throws IOException {
    long value = 0;
    for (int shift = 0; shift < 64; shift += 8) {
      int next = input.read();
      if (next < 0) {
        throw new EOFException("truncated factor-leaf stream");
      }
      value |= (long) next << shift;
    }
    return value;
  }

  private static BigInteger collapse(List<BigInteger> products) {
    if (products.isEmpty()) {
      return BigInteger.ONE;
    }
    while (products.size() > 1) {
      ArrayList<BigInteger> next = new ArrayList<>((products.size() + 1) / 2);
      for (int index = 0; index < products.size(); index += 2) {
        if (index + 1 == products.size()) {
          next.add(products.get(index));
        } else {
          next.add(products.get(index).multiply(products.get(index + 1)));
        }
      }
      products = next;
    }
    return products.get(0);
  }

  private static BigInteger leafProduct(long[] leaves, int begin) {
    ArrayList<BigInteger> chunks = new ArrayList<>((leaves.length - begin + CHUNK - 1) / CHUNK);
    for (int offset = begin; offset < leaves.length; offset += CHUNK) {
      BigInteger product = BigInteger.ONE;
      int end = Math.min(offset + CHUNK, leaves.length);
      for (int index = offset; index < end; ++index) {
        product = product.multiply(BigInteger.valueOf(leaves[index]));
      }
      chunks.add(product);
    }
    return collapse(chunks);
  }

  private static int squareRootFloor(long value) {
    long root = (long) Math.sqrt((double) value);
    while ((root + 1) <= value / (root + 1)) {
      ++root;
    }
    while (root > value / root) {
      --root;
    }
    return Math.toIntExact(root);
  }

  public static void main(String[] arguments) throws Exception {
    if (arguments.length != 3) {
      throw new IllegalArgumentException(
          "usage: CertifyLeavesExport LEAVES.bin PRIMORIAL.bin LARGE_PRODUCT.bin");
    }
    long started = System.nanoTime();
    Path path = Path.of(arguments[0]);
    long fileSize = Files.size(path);
    long[] leaves;
    try (InputStream input = new BufferedInputStream(Files.newInputStream(path))) {
      byte[] magic = input.readNBytes(8);
      if (!Arrays.equals(magic, new byte[] {'E', '8', '4', '8', 'L', '1', 0, 0})) {
        throw new IllegalArgumentException("bad factor-leaf magic");
      }
      long count = readLittleLong(input);
      if (count <= 0 || count > Integer.MAX_VALUE || fileSize != 16L + 8L * count) {
        throw new IllegalArgumentException("bad factor-leaf count or length");
      }
      leaves = new long[Math.toIntExact(count)];
      for (int index = 0; index < leaves.length; ++index) {
        leaves[index] = readLittleLong(input);
        if (leaves[index] < 2 || leaves[index] > PAIR_BOUND ||
            (index != 0 && leaves[index - 1] >= leaves[index])) {
          throw new IllegalArgumentException("factor leaves out of range/order");
        }
      }
      if (input.read() != -1) {
        throw new IllegalArgumentException("trailing factor-leaf data");
      }
    }

    long maximum = leaves[leaves.length - 1];
    int limit = squareRootFloor(maximum);
    byte[] composite = new byte[limit + 1];
    composite[0] = 1;
    composite[1] = 1;
    for (int prime = 2; (long) prime * prime <= limit; ++prime) {
      if (composite[prime] != 0) {
        continue;
      }
      for (int multiple = prime * prime; multiple <= limit; multiple += prime) {
        composite[multiple] = 1;
      }
    }

    int split = Arrays.binarySearch(leaves, (long) limit + 1L);
    split = split >= 0 ? split : -split - 1;
    for (int index = 0; index < split; ++index) {
      if (composite[Math.toIntExact(leaves[index])] != 0) {
        throw new IllegalStateException("composite small factor leaf " + leaves[index]);
      }
    }

    ArrayList<BigInteger> primeChunks = new ArrayList<>();
    BigInteger chunk = BigInteger.ONE;
    int inChunk = 0;
    int primeCount = 0;
    for (int prime = 2; prime <= limit; ++prime) {
      if (composite[prime] != 0) {
        continue;
      }
      chunk = chunk.multiply(BigInteger.valueOf(prime));
      ++inChunk;
      ++primeCount;
      if (inChunk == CHUNK) {
        primeChunks.add(chunk);
        chunk = BigInteger.ONE;
        inChunk = 0;
      }
    }
    if (inChunk != 0) {
      primeChunks.add(chunk);
    }
    BigInteger primorial = collapse(primeChunks);
    BigInteger largeProduct = leafProduct(leaves, split);
    // Exercise the small-composite branch whenever the production sieve
    // contains the fixture.  Tiny valid test streams remain well-defined.
    if (limit >= 49 && composite[49] == 0) {
      throw new IllegalStateException("negative control accepted 49 as prime");
    }
    Files.write(Path.of(arguments[1]), primorial.toByteArray());
    Files.write(Path.of(arguments[2]), largeProduct.toByteArray());

    double seconds = (System.nanoTime() - started) / 1_000_000_000.0;
    System.out.println("leaf_count=" + leaves.length);
    System.out.println("leaf_min=" + leaves[0]);
    System.out.println("leaf_max=" + maximum);
    System.out.println("sieve_limit=" + limit);
    System.out.println("sieve_prime_count=" + primeCount);
    System.out.println("small_leaf_count=" + split);
    System.out.println("large_leaf_count=" + (leaves.length - split));
    System.out.println("primorial_bit_length=" + primorial.bitLength());
    System.out.println("large_product_bit_length=" + largeProduct.bitLength());
    System.out.println(
        "small_negative_control=" + (limit >= 49 ? "passed" : "not-applicable"));
    System.out.printf("elapsed_seconds=%.3f%n", seconds);
    System.out.println("BATCH FACTOR-LEAF PRODUCTS EXPORTED");
  }
}
