<?php
/**
 * Egypt /eg/ WPCode snippet (type php, location everywhere, auto-insert).
 * Do not wrap in <?php when pasting into WPCode — this file is the repo copy.
 *
 * Activate in wp-admin → WPCode → Add Snippet → PHP → Run Everywhere.
 * WPVibe cannot write WPCode snippets from CLI (approval-gated).
 *
 * What it adds on top of Rank Math term noindex already applied live:
 * - Serve /eg/robots.txt (theme ThemeStatic currently 404s it).
 * - noindex,follow remaining English surfaces under /en/ except privacy-policy
 *   (needed for /eg/en/ which is the posts homepage and has no term/post meta).
 * - Drop /en/ and unused URLs from Rank Math sitemaps.
 */

$egypt_uri = isset( $_SERVER['REQUEST_URI'] ) ? (string) $_SERVER['REQUEST_URI'] : '';

if ( preg_match( '#/robots\.txt(?:$|\?)#', $egypt_uri ) ) {
	header( 'Content-Type: text/plain; charset=utf-8' );
	echo "User-agent: *\n";
	echo "Allow: /\n";
	echo "Disallow: /wp-admin/\n";
	echo "Allow: /wp-admin/admin-ajax.php\n\n";
	echo "Sitemap: https://www.rukn-eltatawer.com/eg/sitemap_index.xml\n";
	exit;
}

$egypt_gsc_should_noindex = static function ( $uri ) {
	if ( ! is_string( $uri ) || '' === $uri ) {
		return false;
	}
	if ( false !== stripos( $uri, 'privacy' ) ) {
		return false;
	}
	if ( false !== strpos( $uri, '/en/' ) ) {
		return true;
	}
	if ( false !== strpos( $uri, 'unused' ) ) {
		return true;
	}
	if ( preg_match( '#/category/(leak|insul|maint|clean)(/|$)#', $uri ) ) {
		return true;
	}
	return false;
};

$egypt_gsc_apply_robots = static function ( $robots ) use ( $egypt_gsc_should_noindex ) {
	$uri = isset( $_SERVER['REQUEST_URI'] ) ? (string) $_SERVER['REQUEST_URI'] : '';
	if ( $egypt_gsc_should_noindex( $uri ) && is_array( $robots ) ) {
		unset( $robots['index'] );
		$robots['noindex'] = true;
		$robots['follow']  = true;
	}
	return $robots;
};

add_filter( 'wp_robots', $egypt_gsc_apply_robots, 99 );
add_filter( 'rank_math/frontend/robots', $egypt_gsc_apply_robots, 99 );

add_action(
	'wp_head',
	static function () use ( $egypt_gsc_should_noindex ) {
		$uri = isset( $_SERVER['REQUEST_URI'] ) ? (string) $_SERVER['REQUEST_URI'] : '';
		if ( $egypt_gsc_should_noindex( $uri ) ) {
			echo '<meta name="robots" content="noindex, follow">' . "\n";
		}
	},
	1
);

add_filter(
	'rank_math/sitemap/entry',
	static function ( $url ) {
		if ( ! is_array( $url ) || empty( $url['loc'] ) || ! is_string( $url['loc'] ) ) {
			return $url;
		}
		$loc = $url['loc'];
		if ( false !== stripos( $loc, 'privacy' ) ) {
			return $url;
		}
		if ( false !== strpos( $loc, '/en/' ) || false !== strpos( $loc, 'unused' ) ) {
			return false;
		}
		if ( preg_match( '#/category/(leak|insul|maint|clean)(/|$)#', $loc ) ) {
			return false;
		}
		return $url;
	},
	10,
	3
);
